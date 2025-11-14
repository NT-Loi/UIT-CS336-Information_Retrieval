import logging
from pathlib import Path
import numpy as np
from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection
from pymongo import MongoClient, UpdateOne
import config
import torch
import os
import pandas as pd

logger = logging.getLogger(__name__)

def setup_milvus_collection(collection_name, schema, index_field, index_params):
    if utility.has_collection(collection_name):
        logger.warning(f"Collection '{collection_name}' already exists. Dropping.")
        utility.drop_collection(collection_name)
    
    collection = Collection(collection_name, schema)
    logger.info(f"Collection '{collection_name}' created.")
    
    logger.info(f"Creating index for field '{index_field}'...")
    collection.create_index(field_name=index_field, index_params=index_params)
    collection.flush()
    logger.info("Index created and data flushed.")
    return collection

def ingest_keyframe_data(collection: Collection):
    logger.info("Ingesting keyframe data into Milvus...")
    root = Path(config.CLIP_FEATURES_DIR)
    for video_path in list(root.iterdir()):
        video_id = video_path.name
        vectors = []
        frame_indices = []
        for pt_file in list(video_path.glob("*.pt")):
            frame_idx = int(pt_file.stem.split("_")[-1])
            vec = torch.load(str(pt_file), map_location="cpu").numpy().astype(np.float32)
            vec = vec.reshape(1, -1)
            vectors.append(vec)
            frame_indices.append(frame_idx)
        vectors = np.vstack(vectors)
        num_vectors = len(vectors)
        entities = [[video_id] * num_vectors, frame_indices, vectors]
        collection.insert(entities)
    collection.flush()
    logger.info("Keyframe data ingestion complete.")

def setup_mongodb_collection(mongo_client, db_name, collection_name, drop_existing=True):
    """
    Setup MongoDB collection for object detection metadata.
    
    Args:
        mongo_client: MongoClient instance
        db_name: Database name
        collection_name: Collection name
        drop_existing: If True, drop existing collection
    
    Returns:
        MongoDB collection instance
    """
    db = mongo_client[db_name]
    
    if drop_existing and collection_name in db.list_collection_names():
        logger.warning(f"MongoDB collection '{collection_name}' already exists. Dropping.")
        db[collection_name].drop()
    
    collection = db[collection_name]
    
    # Create indexes for efficient querying
    collection.create_index([("video_id", 1), ("keyframe_index", 1)], unique=True)
    collection.create_index([("objects.label", 1)])
    collection.create_index([("objects.confidence", 1)])
    
    logger.info(f"MongoDB collection '{collection_name}' created with indexes.")
    return collection

def ingest_object_detection_data(mongo_collection, folder_path):
    """
    Ingest object detection metadata into MongoDB.
    """
    logger.info("Ingesting object detection data into MongoDB...")
    
    if not os.path.isdir(folder_path):
        logger.error(f"Object detection directory not found: {folder_path}")
        return
    
    for filename in os.listdir(folder_path):
        if filename.endswith("_rfdetr_results.csv"):
            full_path = os.path.join(folder_path, filename)
            video_id = filename.replace("_rfdetr_results.csv", "")
            
            logger.info(f"--- Processing file: {os.path.basename(full_path)} ---")

            try:
                df = pd.read_csv(full_path)
                df.columns = df.columns.str.strip()
                grouped = df.groupby('frame')

                bulk_operations = []
                for frame_index, group in grouped:
                    frame_index = int(frame_index.replace("keyframe_", "").replace(".webp", ""))
                    objects_list = group.apply(
                        lambda row: {
                            'class': row['class'],
                            'confidence': float(row['confidence']),
                            'bounding_box': {
                                'x': int(row['x']),
                                'y': int(row['y']),
                                'width': int(row['width']),
                                'height': int(row['height'])
                            }
                        },
                        axis=1
                    ).tolist()
                    bulk_operations.append(
                        UpdateOne(
                            {"video_id": video_id, "keyframe_index": int(frame_index)},
                            {"$set": {"objects": objects_list}},
                            upsert=True
                        )
                    )

                logger.info(f"Executing bulk upsert for {len(bulk_operations)} frames for video_id '{video_id}'...")
                result = mongo_collection.bulk_write(bulk_operations)
                logger.info(f"Insert/Update complete for '{video_id}'. Inserted: {result.upserted_count}, Updated: {result.modified_count}\n")
            except Exception as e:
                logger.error(f"An error occurred while processing {full_path}: {e}")
    logger.info(f"Object detection data ingestion complete.")

def main():
    # --- Milvus Ingestion ---
    connections.connect("default", host=config.MILVUS_HOST, port=config.MILVUS_PORT)
    kf_fields = [
        FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="video_id", dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name="keyframe_index", dtype=DataType.INT64),
        FieldSchema(name="keyframe_vector", dtype=DataType.FLOAT_VECTOR, dim=config.VECTOR_DIMENSION)
    ]
    kf_schema = CollectionSchema(kf_fields, "Keyframe vectors")
    kf_index_params = {"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
    
    kf_collection = setup_milvus_collection(config.KEYFRAME_COLLECTION_NAME, kf_schema, "keyframe_vector", kf_index_params)
    ingest_keyframe_data(kf_collection)

    # --- MongoDB Ingestion ---
    mongo_client = MongoClient(config.MONGO_URI)
    object_collection = setup_mongodb_collection(
        mongo_client,
        config.MONGO_DB_NAME,
        config.MONGO_OBJECT_COLLECTION,
        drop_existing=True
    )
    ingest_object_detection_data(object_collection, folder_path=config.OBJECT_DETECTION_DIR)

    logger.info("--- DATA INGESTION COMPLETE ---")

    # Close connections
    mongo_client.close()