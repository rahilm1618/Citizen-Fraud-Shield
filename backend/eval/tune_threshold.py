import asyncio
import json
import os
from pathlib import Path

from app.database import async_session_factory
from app.services.embedding_service import get_embedding
from app.services.session_service import get_closest_patterns

async def get_evaluation_data():
    eval_dir = Path(__file__).parent
    json_path = eval_dir / "threshold_examples.json"
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    positives = data.get("positive", [])
    negatives = data.get("negative", [])
    
    results = []
    
    async with async_session_factory() as db:
        # Process Positives
        for item in positives:
            text = item["transcript"]
            expected = item["expected_category"]
            emb = await get_embedding(text)
            matches = await get_closest_patterns(db, emb, limit=1)
            
            if matches:
                pattern, dist = matches[0]
                matched_cat = pattern.category
                distance = dist
            else:
                matched_cat = "None"
                distance = 1.0
                
            results.append({
                "type": "POS", 
                "distance": distance, 
                "text": text,
                "expected_category": expected,
                "matched_category": matched_cat
            })
            
        # Process Negatives
        for item in negatives:
            text = item["transcript"]
            emb = await get_embedding(text)
            matches = await get_closest_patterns(db, emb, limit=1)
            
            if matches:
                pattern, dist = matches[0]
                matched_cat = pattern.category
                distance = dist
            else:
                matched_cat = "None"
                distance = 1.0
                
            results.append({
                "type": "NEG", 
                "distance": distance, 
                "text": text,
                "expected_category": "N/A (Normal)",
                "matched_category": matched_cat
            })
            
    return results

async def evaluate_thresholds():
    results = await get_evaluation_data()
    
    print("=" * 80)
    print("RAG THRESHOLD TUNING EVALUATION")
    print("=" * 80)
    
    print(f"\n{ 'EXAMPLE TEXT (TRUNCATED)':<50} | { 'EXPECTED CATEGORY':<18} | { 'MATCHED CATEGORY':<18} | { 'DIST':<5} | TYPE")
    print("-" * 115)
    
    for r in results:
        text = r["text"]
        trunc_text = text[:47] + "..." if len(text) > 47 else text.ljust(50)
        print(f"{trunc_text:<50} | {r['expected_category']:<18} | {r['matched_category']:<18} | {r['distance']:.3f} | {r['type']}")
            
    print("-" * 115)
    
    # Summary Stats
    pos_dists = [r["distance"] for r in results if r["type"] == "POS"]
    neg_dists = [r["distance"] for r in results if r["type"] == "NEG"]
    
    max_pos = max(pos_dists) if pos_dists else 1.0
    min_neg = min(neg_dists) if neg_dists else 0.0
    
    print("\n" + "=" * 40)
    print("SUMMARY STATS")
    print("=" * 40)
    print(f"Max distance for POSITIVES: {max_pos:.4f} (Lower is better, want strict match)")
    print(f"Min distance for NEGATIVES: {min_neg:.4f} (Higher is better, want no match)")
    if min_neg > max_pos:
        print(f"GAP DETECTED: Yes, clean gap of {min_neg - max_pos:.4f} between classes!")
    else:
        print(f"NO CLEAN GAP: Overlap of {max_pos - min_neg:.4f}. Threshold must compromise.")
        
    # Threshold Sweep Table
    print("\n" + "=" * 60)
    print("THRESHOLD SWEEP (0.15 to 0.60)")
    print("=" * 60)
    print(f"{'THRESHOLD':<10} | {'POS KEPT (RECALL)':<20} | {'NEG REJECTED (SPECIFICITY)':<25}")
    print("-" * 60)
    
    for t in range(15, 65, 5):
        threshold = t / 100.0
        
        # Positive: we want distance <= threshold (kept)
        pos_kept = sum(1 for d in pos_dists if d <= threshold)
        
        # Negative: we want distance > threshold (rejected/filtered)
        neg_rejected = sum(1 for d in neg_dists if d > threshold)
        
        print(f"{threshold:.2f}       | {pos_kept}/{len(pos_dists)} ({(pos_kept/len(pos_dists))*100:5.1f}%)        | {neg_rejected}/{len(neg_dists)} ({(neg_rejected/len(neg_dists))*100:5.1f}%)")
        

if __name__ == "__main__":
    # Ensure working directory is correctly handling env paths for config if needed, though 
    # Python -m eval.tune_threshold naturally loads the .env via pydantic-settings in app.config
    asyncio.run(evaluate_thresholds())
