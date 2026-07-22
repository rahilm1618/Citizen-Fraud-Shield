import asyncio
import os
from pathlib import Path
import matplotlib.pyplot as plt
from sqlalchemy import select, func

from app.database import async_session_factory
from app.models import ScamPattern
from eval.tune_threshold import get_evaluation_data

async def generate_report():
    print("Gathering evaluation data...")
    results = await get_evaluation_data()
    
    print("Querying category coverage...")
    async with async_session_factory() as db:
        stmt = select(ScamPattern.category, func.count()).group_by(ScamPattern.category)
        db_res = await db.execute(stmt)
        category_counts = {cat: count for cat, count in db_res.all()}
        
    low_coverage_categories = [cat for cat, count in category_counts.items() if count < 2]
    
    # Process Metrics
    pos_results = [r for r in results if r["type"] == "POS"]
    neg_results = [r for r in results if r["type"] == "NEG"]
    
    pos_dists = [r["distance"] for r in pos_results]
    neg_dists = [r["distance"] for r in neg_results]
    
    # 1. Generate Distance Distribution Plot
    print("Generating distribution plot...")
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    plt.figure(figsize=(10, 4))
    # Y-axis will just be 0 for all dots, we spread them out slightly for visibility (jitter)
    import random
    
    # Plot positives (green)
    pos_y = [random.uniform(-0.1, 0.1) for _ in pos_dists]
    plt.scatter(pos_dists, pos_y, color='green', label='Positive (Scam)', alpha=0.7, s=100, edgecolors='black')
    
    # Plot negatives (blue)
    neg_y = [random.uniform(-0.1, 0.1) for _ in neg_dists]
    plt.scatter(neg_dists, neg_y, color='blue', label='Negative (Normal)', alpha=0.7, s=100, edgecolors='black')
    
    # Add threshold line
    plt.axvline(x=0.50, color='red', linestyle='--', label='Threshold (0.50)')
    
    plt.title('Cosine Distance Distribution')
    plt.xlabel('Cosine Distance (Lower = More Similar to Scam)')
    plt.yticks([])  # Hide y axis
    plt.legend()
    plt.tight_layout()
    
    plot_path = output_dir / "distance_distribution.png"
    plt.savefig(plot_path)
    plt.close()
    
    # 2. Build Markdown Report
    print("Writing markdown report...")
    md_path = output_dir / "threshold_report.md"
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# RAG Threshold Tuning Report\n\n")
        
        # Methodology
        f.write("## Methodology\n")
        f.write("This evaluation tests the RAG (Retrieval-Augmented Generation) vector matching step in isolation. "
                "It directly queries the production Supabase database using the HuggingFace embedding model, completely "
                "bypassing the LLM reasoning phase. This allows us to mathematically tune the similarity distance threshold "
                "to find the optimal balance between catching true scams and ignoring normal conversations.\n\n")
                
        # Results Table
        f.write("## Results Table\n")
        f.write("| Example Text (Truncated) | Expected Category | Matched Category | Distance | Type |\n")
        f.write("|--------------------------|-------------------|------------------|----------|------|\n")
        for r in results:
            trunc = r['text'][:60].replace("\n", " ") + "..." if len(r['text']) > 60 else r['text'].replace("\n", " ")
            f.write(f"| {trunc} | {r['expected_category']} | {r['matched_category']} | {r['distance']:.3f} | {r['type']} |\n")
        f.write("\n")
        
        # Category Difficulty Breakdown
        f.write("## Category Difficulty & Coverage\n")
        f.write("### Positive Examples Breakdown\n")
        f.write("| Expected Category | Distance | Matched? |\n")
        f.write("|-------------------|----------|----------|\n")
        for r in pos_results:
            is_match = "✅ Yes" if r['expected_category'] == r['matched_category'] else "❌ No"
            f.write(f"| {r['expected_category']} | {r['distance']:.3f} | {is_match} |\n")
        f.write("\n")
        
        f.write("### Low Coverage Warning\n")
        f.write("The following categories have less than 2 seeded examples in the database, meaning they are unvalidated or have low coverage:\n")
        if low_coverage_categories:
            for cat in low_coverage_categories:
                f.write(f"- ⚠️ **{cat}**\n")
        else:
            f.write("- ✅ All categories have sufficient coverage (>= 2 examples).\n")
        f.write("\n")
        
        # Sweep Table
        f.write("## Threshold Sweep\n")
        f.write("| Threshold | Recall (Pos Kept) | Specificity (Neg Rejected) | Precision | F1 Score |\n")
        f.write("|-----------|-------------------|----------------------------|-----------|----------|\n")
        
        for t in range(15, 65, 5):
            threshold = t / 100.0
            
            # Positives kept (True Positives)
            tp = sum(1 for d in pos_dists if d <= threshold)
            # Positives rejected (False Negatives)
            fn = len(pos_dists) - tp
            
            # Negatives rejected (True Negatives)
            tn = sum(1 for d in neg_dists if d > threshold)
            # Negatives kept (False Positives)
            fp = len(neg_dists) - tn
            
            recall = tp / len(pos_dists) if pos_dists else 0.0
            specificity = tn / len(neg_dists) if neg_dists else 0.0
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            
            if precision + recall > 0:
                f1 = 2 * (precision * recall) / (precision + recall)
            else:
                f1 = 0.0
                
            recall_str = f"{tp}/{len(pos_dists)} ({recall*100:.1f}%)"
            spec_str = f"{tn}/{len(neg_dists)} ({specificity*100:.1f}%)"
            prec_str = f"{precision*100:.1f}%"
            f1_str = f"{f1:.3f}"
            
            # Bold the 0.50 row
            if abs(threshold - 0.50) < 0.01:
                f.write(f"| **{threshold:.2f}** | **{recall_str}** | **{spec_str}** | **{prec_str}** | **{f1_str}** |\n")
            else:
                f.write(f"| {threshold:.2f} | {recall_str} | {spec_str} | {prec_str} | {f1_str} |\n")
        f.write("\n")
        
        # Embedded Image
        f.write("## Distance Distribution\n")
        f.write("![Distance Distribution](./distance_distribution.png)\n\n")
        
        # Findings Placeholder
        f.write("## Findings\n")
        f.write("<!-- Add your interview notes and interpretation here -->\n")
        
    print(f"Report generated successfully at {md_path}")

if __name__ == "__main__":
    asyncio.run(generate_report())
