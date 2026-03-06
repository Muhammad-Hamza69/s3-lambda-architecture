# Architecture Diagram

<img width="1004" height="424" alt="Untitled Diagram drawio (3)" src="https://github.com/user-attachments/assets/35e6b3d7-457d-4f3b-96b9-2c47122d0b1c" />

If 1000 files are uploaded to S3 at the same time, Lambda can process them concurrently. If more than 1000 events occur simultaneously, Lambda may throttle additional invocations due to concurrency limits, but the events are retried automatically. However, this can introduce latency and throttling. 

<img width="1324" height="464" alt="Untitled Diagram drawio (4)" src="https://github.com/user-attachments/assets/a0cda868-2bbe-4e8d-91d6-36264c3b3a6d" />

To handle high event volumes reliably, it is recommended to use an S3 → SQS → Lambda architecture. When a large number of files (e.g., 10,000) are uploaded to S3, event notifications send messages to SQS. The messages remain in the queue, and Lambda polls the queue and processes them in batches based on available concurrency until all messages are processed.

# Automating-S3-to-Lambda-Triggers
Step-by-Step Guide to Deploying and Optimizing Your First Lambda Function
