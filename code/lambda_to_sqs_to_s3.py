import csv
import json
import boto3
from io import StringIO
from datetime import datetime

s3_client = boto3.client('s3')

def lambda_handler(event, context):

    print("Received event:", json.dumps(event))

    records_to_process = []

    # Detect if event is from SQS
    if 'Records' in event and 'body' in event['Records'][0]:
        print("Event received via SQS")
        for sqs_record in event['Records']:
            try:
                body = json.loads(sqs_record['body'])
                s3_records = body.get('Records', [])
                print(f"Found {len(s3_records)} S3 records in SQS message")
                records_to_process.extend(s3_records)
            except Exception as e:
                print(f"Failed to parse SQS body: {e}")
    else:
        print("Direct S3 trigger detected")
        records_to_process = event.get('Records', [])

    if not records_to_process:
        print("No records to process. Exiting.")
        return {'statusCode': 200, 'body': json.dumps('No records found')}

    # Process each S3 record
    for record in records_to_process:
        try:
            bucket_name = record['s3']['bucket']['name']
            input_file_key = record['s3']['object']['key']

            print(f"Processing file: {input_file_key} from bucket: {bucket_name}")

            if not input_file_key.lower().startswith('input/'):
                print("Skipping file (not in input/ folder)")
                continue

            # Fetch CSV from S3
            response = s3_client.get_object(Bucket=bucket_name, Key=input_file_key)
            file_content = response['Body'].read().decode('utf-8')

            csv_file = StringIO(file_content)
            reader = csv.DictReader(csv_file)

            if not reader.fieldnames:
                print(f"No headers found in CSV: {input_file_key}. Skipping.")
                continue
            else:
                print(f"CSV headers: {reader.fieldnames}")

            fieldnames = reader.fieldnames + ['close_pct_change', 'created_at']
            output_csv = StringIO()
            writer = csv.DictWriter(output_csv, fieldnames=fieldnames)
            writer.writeheader()

            rows_written = 0
            for row in reader:
                # Transformations
                row['date'] = transform_date(row.get('date', ''))
                row['volume'] = adjust_volume(row.get('volume', ''))

                try:
                    if float(row.get('low', 0)) == 0:
                        row['low'] = str(
                            (float(row.get('open', 0)) + float(row.get('close', 0))) / 2
                        )
                except Exception as e:
                    print(f"Failed to adjust low value: {e}")

                row['close_pct_change'] = recalculate_pct_change(
                    row.get('open', 0),
                    row.get('close', 0)
                )
                row['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                writer.writerow(row)
                rows_written += 1

            if rows_written == 0:
                print(f"No valid rows found in CSV: {input_file_key}. Skipping upload.")
                continue

            # Prepare output key
            output_file_key = input_file_key.replace('input/', 'output/')

            # Upload to S3
            print(f"Uploading processed file to: {output_file_key}")
            s3_client.put_object(
                Bucket=bucket_name,
                Key=output_file_key,
                Body=output_csv.getvalue()
            )
            print(f"Successfully uploaded to {output_file_key}")

        except Exception as e:
            print(f"Error processing file {input_file_key}: {str(e)}")
            continue  # Don't crash Lambda, move to next file

    return {
        'statusCode': 200,
        'body': json.dumps('Processing completed successfully')
    }


# Helper functions
def transform_date(date_str):
    try:
        return datetime.strptime(date_str, '%m/%d/%Y').strftime('%Y-%m-%d')
    except:
        return date_str

def adjust_volume(volume):
    try:
        if int(volume) < 100000:
            return 'N/A'
        return volume
    except:
        return volume

def recalculate_pct_change(open_price, close_price):
    try:
        open_price = float(open_price)
        close_price = float(close_price)
        if open_price == 0:
            return '0'
        return str(((close_price - open_price) / open_price) * 100)
    except:
        return '0'

def clean_time_format(time_str):
    try:
        time_parts = time_str.split(':')
        return f"{time_parts[0].zfill(2)}:{time_parts[1].zfill(2)}"
    except:
        return time_str
