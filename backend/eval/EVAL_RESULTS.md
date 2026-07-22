# RAG Threshold Evaluation Results

The offline evaluation pipeline for tuning the `rag_similarity_threshold` isolates vector distance math from LLM outputs, utilizing the production Supabase database.

## Output Log

```text
================================================================================
RAG THRESHOLD TUNING EVALUATION
================================================================================

EXAMPLE TEXT (TRUNCATED)                           | EXPECTED CATEGORY  | MATCHED CATEGORY   | DIST  | TYPE
-------------------------------------------------------------------------------------------------------------------
Sir I am calling from CBI cyber cell Mumbai. Yo... | digital_arrest     | digital_arrest     | 0.252 | POS
This is an automated message from the courier c... | customs_scam       | customs_scam       | 0.430 | POS
Dear customer your electricity connection will ... | electricity_scam   | electricity_scam   | 0.188 | POS
Congratulations, we are offering you a simple w... | work_from_home     | work_from_home     | 0.176 | POS
You borrowed 5000 rupees from our instant loan ... | loan_fraud         | loan_fraud         | 0.244 | POS
Hello, this is regarding your bank KYC. Your ac... | kyc_fraud          | kyc_fraud          | 0.367 | POS
Hi I saw your profile and felt an instant conne... | romance_scam       | impersonation      | 0.543 | POS
We regret to inform you that your computer has ... | tech_support_scam  | tech_support_scam  | 0.301 | POS
Congratulations, your mobile number has won 25 ... | lottery_scam       | lottery_scam       | 0.224 | POS
Hey, are you still up for dinner tonight? I was... | N/A (Normal)       | impersonation      | 0.705 | NEG
Hi, I'm calling to confirm your appointment wit... | N/A (Normal)       | impersonation      | 0.706 | NEG
Good morning, this is regarding the order you p... | N/A (Normal)       | customs_scam       | 0.654 | NEG
Mom, I landed safely, the flight was a bit dela... | N/A (Normal)       | impersonation      | 0.645 | NEG
Thanks for calling customer support. I can see ... | N/A (Normal)       | impersonation      | 0.535 | NEG
So the meeting got pushed to 3 PM because half ... | N/A (Normal)       | electricity_scam   | 0.553 | NEG
Hey it's been ages, how have you been? I heard ... | N/A (Normal)       | customs_scam       | 0.786 | NEG
Your cab is arriving in 3 minutes, a white Swif... | N/A (Normal)       | digital_arrest     | 0.709 | NEG
This is a reminder that your library books are ... | N/A (Normal)       | impersonation      | 0.660 | NEG
-------------------------------------------------------------------------------------------------------------------

========================================
SUMMARY STATS
========================================
Max distance for POSITIVES: 0.5425 (Lower is better, want strict match)
Min distance for NEGATIVES: 0.5354 (Higher is better, want no match)
NO CLEAN GAP: Overlap of 0.0072. Threshold must compromise.

============================================================
THRESHOLD SWEEP (0.15 to 0.60)
============================================================
THRESHOLD  | POS KEPT (RECALL)    | NEG REJECTED (SPECIFICITY)
------------------------------------------------------------
0.15       | 0/9 (  0.0%)        | 9/9 (100.0%)
0.20       | 2/9 ( 22.2%)        | 9/9 (100.0%)
0.25       | 4/9 ( 44.4%)        | 9/9 (100.0%)
0.30       | 5/9 ( 55.6%)        | 9/9 (100.0%)
0.35       | 6/9 ( 66.7%)        | 9/9 (100.0%)
0.40       | 7/9 ( 77.8%)        | 9/9 (100.0%)
0.45       | 8/9 ( 88.9%)        | 9/9 (100.0%)
0.50       | 8/9 ( 88.9%)        | 9/9 (100.0%)
0.55       | 9/9 (100.0%)        | 8/9 ( 88.9%)
0.60       | 9/9 (100.0%)        | 7/9 ( 77.8%)
```

## Data Insights
- A default of `0.35` acts fairly strictly, keeping `66.7%` of real scams and rejecting `100%` of small talk. 
- A threshold of `0.45` or `0.50` might be optimal if capturing more positive variations (`88.9%` recall) without risking false positives (`100%` rejected negatives) is desired.
- The single overlapping element is the Romance Scam (`0.543`), which was slightly less "scammy" to the embedding model than the Customer Support Refund negative (`0.535`).
