import logging
from pymilvus import connections, Collection
from pymongo import MongoClient
import torch
import config
from utils.text_encoder import TextEncoder

# --- Setup Logging ---
logger = logging.getLogger(__name__)

class VideoRetrievalSystem:
    def __init__(self, re_ingest=False):
        if re_ingest:
            from ingest_data import main
            main()

        logger.info("Initializing Video Retrieval System...")

        # --- Milvus ---
        connections.connect("default", host=config.MILVUS_HOST, port=config.MILVUS_PORT)
        logger.info("Successfully connected to Milvus.")
        self.keyframes_collection = Collection(config.KEYFRAME_COLLECTION_NAME)
        self.keyframes_collection.load()

        # --- MongoDB ---
        mongo_client = MongoClient(config.MONGO_URI)
        mongo_db = mongo_client[config.MONGO_DB_NAME]
        self.object_collection = mongo_db[config.MONGO_OBJECT_COLLECTION]
        logger.info("Successfully connected to MongoDB.")

        # Initialize the text encoder
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.encoder = TextEncoder(device=self.device)

    def clip_search(self, query: str = "", max_results: int = 200) -> list:
        """
        Searching on CLIP embeddings.
        """
        logger.info(f"--- Start searching on CLIP embeddings with query: '{query}' ---")

        if not query:
            logger.warning("Search initiated with no query data.")
            return []

        query_vector = self.encoder.encode(query)
        
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    
        search_results = self.keyframes_collection.search(
            data=query_vector,
            anns_field="keyframe_vector", 
            param=search_params,
            limit=max_results,
            output_fields=["video_id", "keyframe_index"]
        )

        keyframe_scores = []
        if search_results:
            for hit in search_results[0]:
                keyframe_scores.append({'video_id': hit.entity.get('video_id'),
                                        'keyframe_index': hit.entity.get('keyframe_index'),
                                        'vector_score': hit.distance})                                       
            
        logger.info(f"CLIP: Found {len(keyframe_scores)} potential keyframes.")
        return keyframe_scores
        
    def object_search(self, queries: list[dict], projection: dict = None) -> list[dict]:
        """
        Search keyframes where objects match all specified query conditions.
        Args:
            queries (list[dict]): A list of query dictionaries. Example format:
                [
                    {'label': 'car', 'confidence': 0.5, 'min_instances': 1, 'max_instances': 3},
                    {'label': 'person', 'confidence': 0.7, 'min_instances': 1}
                ]
        Returns:
            list[dict]: A list of matching documents (keyframes) from the collection.
        """
        if not queries:
            return []
        
        try:
            # Extract all labels for pre-filtering
            labels = list(set(q['label'] for q in queries))
            
            pipeline = [
                # Pre-filter: Only documents that have at least one of the required labels
                {
                    "$match": {
                        "objects.class": {"$in": labels}
                    }
                }
            ]
            
            # Build aggregation conditions
            all_conditions = []
            
            for query in queries:
                label = query['label']
                min_confidence = query.get('confidence', 0.0)
                min_instances = query.get('min_instances')
                max_instances = query.get('max_instances')
                
                if min_instances is None and max_instances is None:
                    raise ValueError(f"Query for label '{label}' must have at least min_instances or max_instances.")
                
                filter_expr = {
                    "$filter": {
                        "input": "$objects",
                        "as": "obj",
                        "cond": {
                            "$and": [
                                {"$eq": ["$$obj.class", label]},
                                {"$gte": ["$$obj.confidence", min_confidence]}
                            ]
                        }
                    }
                }
                
                size_expr = {"$size": filter_expr}
                
                query_conditions = []
                if min_instances is not None:
                    query_conditions.append({"$gte": [size_expr, min_instances]})
                if max_instances is not None:
                    query_conditions.append({"$lte": [size_expr, max_instances]})
                
                if len(query_conditions) == 1:
                    all_conditions.append(query_conditions[0])
                else:
                    all_conditions.append({"$and": query_conditions})
            
            # Add the expression match
            pipeline.append({
                "$match": {
                    "$expr": {"$and": all_conditions} if len(all_conditions) > 1 else all_conditions[0]
                }
            })
            
            # Add projection if specified
            if projection:
                pipeline.append({"$project": projection})
            
            results = list(self.object_collection.aggregate(pipeline))
            logger.info(f"MongoDB: Found {len(results)} keyframes matching queries.")
            return results
            
        except Exception as e:
            logger.error(f"An error occurred during object search: {e}")
            return []
        
# --- Example Usage ---
if __name__ == '__main__':
    searcher = VideoRetrievalSystem()
    query1 = [
        {'label': 'car', 'confidence': 0.5, 'min_instances': 1, 'max_instances': 3},
        {'label': 'person', 'confidence': 0.7, 'min_instances': 1}
    ]
    import time
    print('Start searching')
    start = time.time()
    matching_frames = searcher.object_search(query1, projection={'_id': 1, 'video_id': 1, 'keyframe_id': 1})
    print('Filter take: ', time.time()-start)