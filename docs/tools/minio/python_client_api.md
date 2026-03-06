Python Client API Reference
1. Constructor
Minio(endpoint, access_key=None, secret_key=None, session_token=None, secure=True, region=None, http_client=None, credentials=None)
Initializes a new client object.

Parameters

Param	Type	Description
endpoint	str	Hostname of a S3 service.
access_key	str	(Optional) Access key (aka user ID) of your account in S3 service.
secret_key	str	(Optional) Secret Key (aka password) of your account in S3 service.
session_token	str	(Optional) Session token of your account in S3 service.
secure	bool	(Optional) Flag to indicate to use secure (TLS) connection to S3 service or not.
region	str	(Optional) Region name of buckets in S3 service.
http_client	urllib3.poolmanager.PoolManager	(Optional) Customized HTTP client.
credentials	minio.credentials.Provider	(Optional) Credentials provider of your account in S3 service.
cert_check	bool	(Optional) Flag to check on server certificate for HTTPS connection.
NOTE on concurrent usage: Minio object is thread safe when using the Python threading library. Specifically, it is NOT safe to share it between multiple processes, for example when using multiprocessing.Pool. The solution is simply to create a new Minio object in each process, and not share it between processes.

Example

from minio import Minio

# Create client with anonymous access.
client = Minio("play.min.io")

# Create client with access and secret key.
client = Minio("s3.amazonaws.com", "ACCESS-KEY", "SECRET-KEY")

# Create client with access key and secret key with specific region.
client = Minio(
    "play.minio.io:9000",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    region="my-region",
)

# Create client with custom HTTP client using proxy server.
import urllib3
client = Minio(
    "SERVER:PORT",
    access_key="ACCESS_KEY",
    secret_key="SECRET_KEY",
    secure=True,
    http_client=urllib3.ProxyManager(
        "https://PROXYSERVER:PROXYPORT/",
        timeout=urllib3.Timeout.DEFAULT_TIMEOUT,
        cert_reqs="CERT_REQUIRED",
        retries=urllib3.Retry(
            total=5,
            backoff_factor=0.2,
            status_forcelist=[500, 502, 503, 504],
        ),
    ),
)
Bucket operations	Object operations
make_bucket	append_object
list_buckets	get_object
bucket_exists	put_object
remove_bucket	copy_object
list_objects	compose_object
get_bucket_versioning	stat_object
set_bucket_versioning	remove_object
delete_bucket_replication	remove_objects
get_bucket_replication	fput_object
set_bucket_replication	fget_object
delete_bucket_lifecycle	select_object_content
get_bucket_lifecycle	delete_object_tags
set_bucket_lifecycle	get_object_tags
delete_bucket_tags	set_object_tags
get_bucket_tags	enable_object_legal_hold
set_bucket_tags	disable_object_legal_hold
delete_bucket_policy	is_object_legal_hold_enabled
get_bucket_policy	get_object_retention
set_bucket_policy	set_object_retention
delete_bucket_notification	presigned_get_object
get_bucket_notification	presigned_put_object
set_bucket_notification	presigned_post_policy
listen_bucket_notification	get_presigned_url
delete_bucket_encryption	upload_snowball_objects
get_bucket_encryption	
set_bucket_encryption	
delete_object_lock_config	
get_object_lock_config	
set_object_lock_config	
2. Bucket operations

make_bucket(bucket_name, location=‘us-east-1’, object_lock=False)
Create a bucket with region and object lock.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
location	str	Region in which the bucket will be created.
object_lock	bool	Flag to set object-lock feature.
Example

# Create bucket.
client.make_bucket("my-bucket")

# Create bucket on specific region.
client.make_bucket("my-bucket", "us-west-1")

# Create bucket with object-lock feature on specific region.
client.make_bucket("my-bucket", "eu-west-2", object_lock=True)

list_buckets()
List information of all accessible buckets.

Parameters

Return
List of Bucket
Example

buckets = client.list_buckets()
for bucket in buckets:
    print(bucket.name, bucket.creation_date)

bucket_exists(bucket_name)
Check if a bucket exists.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Example

if client.bucket_exists("my-bucket"):
    print("my-bucket exists")
else:
    print("my-bucket does not exist")

remove_bucket(bucket_name)
Remove an empty bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Example

client.remove_bucket("my-bucket")

list_objects(bucket_name, prefix=None, recursive=False, start_after=None, include_user_meta=False, include_version=False, use_api_v1=False, use_url_encoding_type=True, extra_headers=None, extra_query_params=None)
Lists object information of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
prefix	str	Object name starts with prefix.
recursive	bool	List recursively than directory structure emulation.
start_after	str	List objects after this key name.
include_user_meta	bool	MinIO specific flag to control to include user metadata.
include_version	bool	Flag to control whether include object versions.
use_api_v1	bool	Flag to control to use ListObjectV1 S3 API or not.
use_url_encoding_type	bool	Flag to control whether URL encoding type to be used or not.
extra_headers	dict	Extra HTTP headers for advanced usage.
extra_query_params	dict	Extra query parameters for advanced usage.
Return Value

Return
An iterator of Object
Example

# List objects information.
objects = client.list_objects("my-bucket")
for obj in objects:
    print(obj)

# List objects information whose names starts with "my/prefix/".
objects = client.list_objects("my-bucket", prefix="my/prefix/")
for obj in objects:
    print(obj)

# List objects information recursively.
objects = client.list_objects("my-bucket", recursive=True)
for obj in objects:
    print(obj)

# List objects information recursively whose names starts with
# "my/prefix/".
objects = client.list_objects(
    "my-bucket", prefix="my/prefix/", recursive=True,
)
for obj in objects:
    print(obj)

# List objects information recursively after object name
# "my/prefix/world/1".
objects = client.list_objects(
    "my-bucket", recursive=True, start_after="my/prefix/world/1",
)
for obj in objects:
    print(obj)

get_bucket_policy(bucket_name)
Get bucket policy configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Return Value

Param
Bucket policy configuration as JSON string.
Example

policy = client.get_bucket_policy("my-bucket")

set_bucket_policy(bucket_name, policy)
Set bucket policy configuration to a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Policy	str	Bucket policy configuration as JSON string.
Example

# Example anonymous read-only bucket policy.
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
            "Resource": "arn:aws:s3:::my-bucket",
        },
        {
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::my-bucket/*",
        },
    ],
}
client.set_bucket_policy("my-bucket", json.dumps(policy))

# Example anonymous read-write bucket policy.
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": [
                "s3:GetBucketLocation",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads",
            ],
            "Resource": "arn:aws:s3:::my-bucket",
        },
        {
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListMultipartUploadParts",
                "s3:AbortMultipartUpload",
            ],
            "Resource": "arn:aws:s3:::my-bucket/images/*",
        },
    ],
}
client.set_bucket_policy("my-bucket", json.dumps(policy))

delete_bucket_policy(bucket_name)
Delete bucket policy configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Example

client.delete_bucket_policy("my-bucket")

get_bucket_notification(bucket_name)
Get notification configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Return Value

Param
NotificationConfig object.
Example

config = client.get_bucket_notification("my-bucket")

set_bucket_notification(bucket_name, config)
Set notification configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
config	NotificationConfig	Notification configuration.
Example

config = NotificationConfig(
    queue_config_list=[
        QueueConfig(
            "QUEUE-ARN-OF-THIS-BUCKET",
            ["s3:ObjectCreated:*"],
            config_id="1",
            prefix_filter_rule=PrefixFilterRule("abc"),
        ),
    ],
)
client.set_bucket_notification("my-bucket", config)

delete_bucket_notification(bucket_name)
Delete notification configuration of a bucket. On success, S3 service stops notification of events previously set of the bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Example

client.delete_bucket_notification("my-bucket")

listen_bucket_notification(bucket_name, prefix=’’, suffix=’’, events=(‘s3:ObjectCreated:*’, ‘s3:ObjectRemoved:*’, ‘s3:ObjectAccessed:*’))
Listen events of object prefix and suffix of a bucket. Caller should iterate returned iterator to read new events.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
prefix	str	Listen events of object starts with prefix.
suffix	str	Listen events of object ends with suffix.
events	list	Events to listen.
Return Value

Param
Iterator of event records as dict
with client.listen_bucket_notification(
    "my-bucket",
    prefix="my-prefix/",
    events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"],
) as events:
    for event in events:
        print(event)

get_bucket_encryption(bucket_name)
Get encryption configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Return Value

Param
SSEConfig object.
Example

config = client.get_bucket_encryption("my-bucket")

set_bucket_encryption(bucket_name, config)
Set encryption configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
config	SSEConfig	Server-side encryption configuration.
Example

client.set_bucket_encryption(
    "my-bucket", SSEConfig(Rule.new_sse_s3_rule()),
)

delete_bucket_encryption(bucket_name)
Delete encryption configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Example

client.delete_bucket_encryption("my-bucket")

get_bucket_versioning(bucket_name)
Get versioning configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Example

config = client.get_bucket_versioning("my-bucket")
print(config.status)

set_bucket_versioning(bucket_name, config)
Set versioning configuration to a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
config	VersioningConfig	Versioning configuration.
Example

client.set_bucket_versioning("my-bucket", VersioningConfig(ENABLED))

delete_bucket_replication(bucket_name)
Delete replication configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Example

client.delete_bucket_replication("my-bucket")

get_bucket_replication(bucket_name)
Get replication configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Return
ReplicationConfig object.
Example

config = client.get_bucket_replication("my-bucket")

set_bucket_replication(bucket_name, config)
Set replication configuration to a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
config	ReplicationConfig	Replication configuration.
Example

config = ReplicationConfig(
    "REPLACE-WITH-ACTUAL-ROLE",
    [
        Rule(
            Destination(
                "REPLACE-WITH-ACTUAL-DESTINATION-BUCKET-ARN",
            ),
            ENABLED,
            delete_marker_replication=DeleteMarkerReplication(
                DISABLED,
            ),
            rule_filter=Filter(
                AndOperator(
                    "TaxDocs",
                    {"key1": "value1", "key2": "value2"},
                ),
            ),
            rule_id="rule1",
            priority=1,
        ),
    ],
)
client.set_bucket_replication("my-bucket", config)

delete_bucket_lifecycle(bucket_name)
Delete lifecycle configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Example

client.delete_bucket_lifecycle("my-bucket")

get_bucket_lifecycle(bucket_name)
Get lifecycle configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Return
LifecycleConfig object.
Example

config = client.get_bucket_lifecycle("my-bucket")

set_bucket_lifecycle(bucket_name, config)
Set lifecycle configuration to a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
config	LifecycleConfig	Lifecycle configuration.
Example

config = LifecycleConfig(
    [
        Rule(
            ENABLED,
            rule_filter=Filter(prefix="documents/"),
            rule_id="rule1",
            transition=Transition(days=30, storage_class="GLACIER"),
        ),
        Rule(
            ENABLED,
            rule_filter=Filter(prefix="logs/"),
            rule_id="rule2",
            expiration=Expiration(days=365),
        ),
    ],
)
client.set_bucket_lifecycle("my-bucket", config)

delete_bucket_tags(bucket_name)
Delete tags configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Example

client.delete_bucket_tags("my-bucket")

get_bucket_tags(bucket_name)
Get tags configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Return
Tags object.
Example

tags = client.get_bucket_tags("my-bucket")

set_bucket_tags(bucket_name, tags)
Set tags configuration to a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
tags	Tags	Tags configuration.
Example

tags = Tags.new_bucket_tags()
tags["Project"] = "Project One"
tags["User"] = "jsmith"
client.set_bucket_tags("my-bucket", tags)

delete_object_lock_config(bucket_name)
Delete object-lock configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Example

client.delete_object_lock_config("my-bucket")

get_object_lock_config(bucket_name)
Get object-lock configuration of a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
Return
ObjectLockConfig object.
Example

config = client.get_object_lock_config("my-bucket")

set_object_lock_config(bucket_name, config)
Set object-lock configuration to a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
config	ObjectLockConfig	Object-Lock configuration.
Example

config = ObjectLockConfig(GOVERNANCE, 15, DAYS)
client.set_object_lock_config("my-bucket", config)
3. Object operations

append_object(bucket_name, object_name, data, length, content_type=“application/octet-stream”, metadata=None, sse=None, progress=None, part_size=0, num_parallel_uploads=3, tags=None, retention=None, legal_hold=False)
Appends from a stream to existing object in a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
data	object	An object having callable read() returning bytes object.
length	int	Data size; -1 for unknown size and set valid part_size.
part_size	int	Chunk size.
progress	threading	A progress object.
extra_headers	dict	Extra headers.
Return Value

Return
ObjectWriteResult object.
Example

# Append data.
result = client.append_object(
    "my-bucket", "my-object", io.BytesIO(b"world"), 5,
)
print(f"appended {result.object_name} object; etag: {result.etag}")

# Append data in chunks.
data = urlopen(
    "https://www.kernel.org/pub/linux/kernel/v6.x/linux-6.13.12.tar.xz",
)
result = client.append_object(
    "my-bucket", "my-object", data, 148611164, 5*1024*1024,
)
print(f"appended {result.object_name} object; etag: {result.etag}")

# Append unknown sized data.
data = urlopen(
    "https://www.kernel.org/pub/linux/kernel/v6.x/linux-6.14.3.tar.xz",
)
result = client.append_object(
    "my-bucket", "my-object", data, 149426584, 5*1024*1024,
)
print(f"appended {result.object_name} object; etag: {result.etag}")

get_object(bucket_name, object_name, offset=0, length=0, request_headers=None, ssec=None, version_id=None, extra_query_params=None)
Gets data from offset to length of an object. Returned response should be closed after use to release network resources. To reuse the connection, it’s required to call response.release_conn() explicitly.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
offset	int	Start byte position of object data.
length	int	Number of bytes of object data from offset.
request_headers	dict	Any additional headers to be added with GET request.
ssec	SseCustomerKey	Server-side encryption customer key.
version_id	str	Version-ID of the object.
extra_query_params	dict	Extra query parameters for advanced usage.
Return Value

Return
urllib3.response.HTTPResponse object.
Example

# Get data of an object.
try:
    response = client.get_object("my-bucket", "my-object")
    # Read data from response.
finally:
    response.close()
    response.release_conn()

# Get data of an object of version-ID.
try:
    response = client.get_object(
        "my-bucket", "my-object",
        version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
    )
    # Read data from response.
finally:
    response.close()
    response.release_conn()

# Get data of an object from offset and length.
try:
    response = client.get_object(
        "my-bucket", "my-object", offset=512, length=1024,
    )
    # Read data from response.
finally:
    response.close()
    response.release_conn()

# Get data of an SSE-C encrypted object.
try:
    response = client.get_object(
        "my-bucket", "my-object",
        ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
    )
    # Read data from response.
finally:
    response.close()
    response.release_conn()

select_object_content(bucket_name, object_name, request)
Select content of an object by SQL expression.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
request	SelectRequest	Select request.
Return Value

Return
A reader contains requested records and progress information as SelectObjectReader
Example

with client.select_object_content(
        "my-bucket",
        "my-object.csv",
        SelectRequest(
            "select * from S3Object",
            CSVInputSerialization(),
            CSVOutputSerialization(),
            request_progress=True,
        ),
) as result:
    for data in result.stream():
        print(data.decode())
    print(result.stats())

fget_object(bucket_name, object_name, file_path, request_headers=None, ssec=None, version_id=None, extra_query_params=None, tmp_file_path=None)
Downloads data of an object to file.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
file_path	str	Name of file to download.
request_headers	dict	Any additional headers to be added with GET request.
ssec	SseCustomerKey	Server-side encryption customer key.
version_id	str	Version-ID of the object.
extra_query_params	dict	Extra query parameters for advanced usage.
tmp_file_path	str	Path to a temporary file.
Return Value

Return
Object information as Object
Example

# Download data of an object.
client.fget_object("my-bucket", "my-object", "my-filename")

# Download data of an object of version-ID.
client.fget_object(
    "my-bucket", "my-object", "my-filename",
    version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
)

# Download data of an SSE-C encrypted object.
client.fget_object(
    "my-bucket", "my-object", "my-filename",
    ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
)

copy_object(bucket_name, object_name, source, sse=None, metadata=None, tags=None, retention=None, legal_hold=False, metadata_directive=None, tagging_directive=None)
Create an object by server-side copying data from another object. In this API maximum supported source object size is 5GiB.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
source	CopySource	Source object information.
sse	Sse	Server-side encryption of destination object.
metadata	dict	Any user-defined metadata to be copied along with destination object.
tags	Tags	Tags for destination object.
retention	Retention	Retention configuration.
legal_hold	bool	Flag to set legal hold for destination object.
metadata_directive	str	Directive used to handle user metadata for destination object.
tagging_directive	str	Directive used to handle tags for destination object.
Return Value

Return
ObjectWriteResult object.
Example

from datetime import datetime, timezone
from minio.commonconfig import REPLACE, CopySource

# copy an object from a bucket to another.
result = client.copy_object(
    "my-bucket",
    "my-object",
    CopySource("my-sourcebucket", "my-sourceobject"),
)
print(result.object_name, result.version_id)

# copy an object with condition.
result = client.copy_object(
    "my-bucket",
    "my-object",
    CopySource(
        "my-sourcebucket",
        "my-sourceobject",
        modified_since=datetime(2014, 4, 1, tzinfo=timezone.utc),
    ),
)
print(result.object_name, result.version_id)

# copy an object from a bucket with replacing metadata.
metadata = {"test_meta_key": "test_meta_value"}
result = client.copy_object(
    "my-bucket",
    "my-object",
    CopySource("my-sourcebucket", "my-sourceobject"),
    metadata=metadata,
    metadata_directive=REPLACE,
)
print(result.object_name, result.version_id)

compose_object(bucket_name, object_name, sources, sse=None, metadata=None, tags=None, retention=None, legal_hold=False)
Create an object by combining data from different source objects using server-side copy.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
sources	list	List of ComposeSource object.
sse	Sse	Server-side encryption of destination object.
metadata	dict	Any user-defined metadata to be copied along with destination object.
tags	Tags	Tags for destination object.
retention	Retention	Retention configuration.
legal_hold	bool	Flag to set legal hold for destination object.
Return Value

Return
ObjectWriteResult object.
Example

from minio.commonconfig import ComposeSource
from minio.sse import SseS3

sources = [
    ComposeSource("my-job-bucket", "my-object-part-one"),
    ComposeSource("my-job-bucket", "my-object-part-two"),
    ComposeSource("my-job-bucket", "my-object-part-three"),
]

# Create my-bucket/my-object by combining source object
# list.
result = client.compose_object("my-bucket", "my-object", sources)
print(result.object_name, result.version_id)

# Create my-bucket/my-object with user metadata by combining
# source object list.
result = client.compose_object(
    "my-bucket",
    "my-object",
    sources,
    metadata={"test_meta_key": "test_meta_value"},
)
print(result.object_name, result.version_id)

# Create my-bucket/my-object with user metadata and
# server-side encryption by combining source object list.
client.compose_object("my-bucket", "my-object", sources, sse=SseS3())
print(result.object_name, result.version_id)

put_object(bucket_name, object_name, data, length, content_type=“application/octet-stream”, metadata=None, sse=None, progress=None, part_size=0, num_parallel_uploads=3, tags=None, retention=None, legal_hold=False)
Uploads data from a stream to an object in a bucket.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
data	object	An object having callable read() returning bytes object.
length	int	Data size; -1 for unknown size and set valid part_size.
content_type	str	Content type of the object.
metadata	dict	Any additional metadata to be uploaded along with your PUT request.
sse	Sse	Server-side encryption.
progress	threading	A progress object.
part_size	int	Multipart part size.
tags	Tags	Tags for the object.
retention	Retention	Retention configuration.
legal_hold	bool	Flag to set legal hold for the object.
Return Value

Return
ObjectWriteResult object.
Example

# Upload data.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload unknown sized data.
data = urlopen(
    "https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.4.81.tar.xz",
)
result = client.put_object(
    "my-bucket", "my-object", data, length=-1, part_size=10*1024*1024,
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with content-type.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    content_type="application/csv",
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with metadata.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    metadata={"My-Project": "one"},
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with customer key type of server-side encryption.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    sse=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with KMS type of server-side encryption.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    sse=SseKMS("KMS-KEY-ID", {"Key1": "Value1", "Key2": "Value2"}),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with S3 type of server-side encryption.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    sse=SseS3(),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with tags, retention and legal-hold.
date = datetime.utcnow().replace(
    hour=0, minute=0, second=0, microsecond=0,
) + timedelta(days=30)
tags = Tags(for_object=True)
tags["User"] = "jsmith"
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    tags=tags,
    retention=Retention(GOVERNANCE, date),
    legal_hold=True,
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with progress bar.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    progress=Progress(),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

fput_object(bucket_name, object_name, file_path, content_type=“application/octet-stream”, metadata=None, sse=None, progress=None, part_size=0, num_parallel_uploads=3, tags=None, retention=None, legal_hold=False)
Uploads data from a file to an object in a bucket.

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
file_path	str	Name of file to upload.
content_type	str	Content type of the object.
metadata	dict	Any additional metadata to be uploaded along with your PUT request.
sse	Sse	Server-side encryption.
progress	threading	A progress object.
part_size	int	Multipart part size.
tags	Tags	Tags for the object.
retention	Retention	Retention configuration.
legal_hold	bool	Flag to set legal hold for the object.
Return Value

Return
ObjectWriteResult object.
Example

# Upload data.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with content-type.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    content_type="application/csv",
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with metadata.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    metadata={"My-Project": "one"},
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with customer key type of server-side encryption.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    sse=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with KMS type of server-side encryption.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    sse=SseKMS("KMS-KEY-ID", {"Key1": "Value1", "Key2": "Value2"}),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with S3 type of server-side encryption.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    sse=SseS3(),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with tags, retention and legal-hold.
date = datetime.utcnow().replace(
    hour=0, minute=0, second=0, microsecond=0,
) + timedelta(days=30)
tags = Tags(for_object=True)
tags["User"] = "jsmith"
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    tags=tags,
    retention=Retention(GOVERNANCE, date),
    legal_hold=True,
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with progress bar.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    progress=Progress(),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

stat_object(bucket_name, object_name, ssec=None, version_id=None, extra_headers=None, extra_query_params=None)
Get object information and metadata of an object.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
ssec	SseCustomerKey	Server-side encryption customer key.
version_id	str	Version ID of the object.
extra_headers	dict	Extra HTTP headers for advanced usage.
extra_query_params	dict	Extra query parameters for advanced usage.
Return Value

Return
Object information as Object
Example

# Get object information.
result = client.stat_object("my-bucket", "my-object")
print(
    "last-modified: {0}, size: {1}".format(
        result.last_modified, result.size,
    ),
)

# Get object information of version-ID.
result = client.stat_object(
    "my-bucket", "my-object",
    version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
)
print(
    "last-modified: {0}, size: {1}".format(
        result.last_modified, result.size,
    ),
)

# Get SSE-C encrypted object information.
result = client.stat_object(
    "my-bucket", "my-object",
    ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
)
print(
    "last-modified: {0}, size: {1}".format(
        result.last_modified, result.size,
    ),
)

remove_object(bucket_name, object_name, version_id=None)
Remove an object.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
version_id	str	Version ID of the object.
Example

# Remove object.
client.remove_object("my-bucket", "my-object")

# Remove version of an object.
client.remove_object(
    "my-bucket", "my-object",
    version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
)

remove_objects(bucket_name, delete_object_list, bypass_governance_mode=False)
Remove multiple objects.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
delete_object_list	iterable	An iterable containing :class:DeleteObject object.
bypass_governance_mode	bool	Bypass Governance retention mode.
Return Value

Return
An iterator containing :class:DeleteError object
Example

# Remove list of objects.
errors = client.remove_objects(
    "my-bucket",
    [
        DeleteObject("my-object1"),
        DeleteObject("my-object2"),
        DeleteObject("my-object3", "13f88b18-8dcd-4c83-88f2-8631fdb6250c"),
    ],
)
for error in errors:
    print("error occurred when deleting object", error)

# Remove a prefix recursively.
delete_object_list = map(
    lambda x: DeleteObject(x.object_name),
    client.list_objects("my-bucket", "my/prefix/", recursive=True),
)
errors = client.remove_objects("my-bucket", delete_object_list)
for error in errors:
    print("error occurred when deleting object", error)

delete_object_tags(bucket_name, object_name, version_id=None)
Delete tags configuration of an object.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
version_id	str	Version ID of the object.
Example

client.delete_object_tags("my-bucket", "my-object")

get_object_tags(bucket_name, object_name, version_id=None)
Get tags configuration of an object.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
version_id	str	Version ID of the object.
Return
Tags object.
Example

tags = client.get_object_tags("my-bucket", "my-object")

set_object_tags(bucket_name, object_name, tags, version_id=None)
Set tags configuration to an object.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
tags	Tags	Tags configuration.
version_id	str	Version ID of the object.
Example

tags = Tags.new_object_tags()
tags["Project"] = "Project One"
tags["User"] = "jsmith"
client.set_object_tags("my-bucket", "my-object", tags)

enable_object_legal_hold(bucket_name, object_name, version_id=None)
Enable legal hold on an object.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
version_id	str	Version ID of the object.
Example

client.enable_object_legal_hold("my-bucket", "my-object")

disable_object_legal_hold(bucket_name, object_name, version_id=None)
Disable legal hold on an object.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
version_id	str	Version ID of the object.
Example

client.disable_object_legal_hold("my-bucket", "my-object")

is_object_legal_hold_enabled(bucket_name, object_name, version_id=None)
Returns true if legal hold is enabled on an object.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
version_id	str	Version ID of the object.
Example

if client.is_object_legal_hold_enabled("my-bucket", "my-object"):
    print("legal hold is enabled on my-object")
else:
    print("legal hold is not enabled on my-object")

get_object_retention(bucket_name, object_name, version_id=None)
Get retention information of an object.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
version_id	str	Version ID of the object.
Return Value

Return
Retention object
Example

config = client.get_object_retention("my-bucket", "my-object")

set_object_retention(bucket_name, object_name, config, version_id=None)
Set retention information to an object.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
config	Retention	Retention configuration.
version_id	str	Version ID of the object.
Example

config = Retention(GOVERNANCE, datetime.utcnow() + timedelta(days=10))
client.set_object_retention("my-bucket", "my-object", config)

presigned_get_object(bucket_name, object_name, expires=timedelta(days=7), response_headers=None, request_date=None, version_id=None, extra_query_params=None)
Get presigned URL of an object to download its data with expiry time and custom request parameters.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
expires	datetime.timedelta	Expiry in seconds; defaults to 7 days.
response_headers	dict	Optional response_headers argument to specify response fields like date, size, type of file, data about server, etc.
request_date	datetime.datetime	Optional request_date argument to specify a different request date. Default is current date.
version_id	str	Version ID of the object.
extra_query_params	dict	Extra query parameters for advanced usage.
Return Value

Return
URL string
Example

# Get presigned URL string to download 'my-object' in
# 'my-bucket' with default expiry (i.e. 7 days).
url = client.presigned_get_object("my-bucket", "my-object")
print(url)

# Get presigned URL string to download 'my-object' in
# 'my-bucket' with two hours expiry.
url = client.presigned_get_object(
    "my-bucket", "my-object", expires=timedelta(hours=2),
)
print(url)

presigned_put_object(bucket_name, object_name, expires=timedelta(days=7))
Get presigned URL of an object to upload data with expiry time and custom request parameters.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
expires	datetime.timedelta	Expiry in seconds; defaults to 7 days.
Return Value

Return
URL string
Example

# Get presigned URL string to upload data to 'my-object' in
# 'my-bucket' with default expiry (i.e. 7 days).
url = client.presigned_put_object("my-bucket", "my-object")
print(url)

# Get presigned URL string to upload data to 'my-object' in
# 'my-bucket' with two hours expiry.
url = client.presigned_put_object(
    "my-bucket", "my-object", expires=timedelta(hours=2),
)
print(url)

presigned_post_policy(policy)
Get form-data of PostPolicy of an object to upload its data using POST method.

Parameters

Param	Type	Description
policy	PostPolicy	Post policy.
Return Value

Return
Form-data containing dict
Example

policy = PostPolicy(
    "my-bucket", datetime.utcnow() + timedelta(days=10),
)
policy.add_starts_with_condition("key", "my/object/prefix/")
policy.add_content_length_range_condition(
    1*1024*1024, 10*1024*1024,
)
form_data = client.presigned_post_policy(policy)

get_presigned_url(method, bucket_name, object_name, expires=timedelta(days=7), response_headers=None, request_date=None, version_id=None, extra_query_params=None)
Get presigned URL of an object for HTTP method, expiry time and custom request parameters.

Parameters

Param	Type	Description
method	str	HTTP method.
bucket_name	str	Name of the bucket.
object_name	str	Object name in the bucket.
expires	datetime.timedelta	Expiry in seconds; defaults to 7 days.
response_headers	dict	Optional response_headers argument to specify response fields like date, size, type of file, data about server, etc.
request_date	datetime.datetime	Optional request_date argument to specify a different request date. Default is current date.
version_id	str	Version ID of the object.
extra_query_params	dict	Extra query parameters for advanced usage.
Return Value

Return
URL string
Example

# Get presigned URL string to delete 'my-object' in
# 'my-bucket' with one day expiry.
url = client.get_presigned_url(
    "DELETE",
    "my-bucket",
    "my-object",
    expires=timedelta(days=1),
)
print(url)

# Get presigned URL string to upload 'my-object' in
# 'my-bucket' with response-content-type as application/json
# and one day expiry.
url = client.get_presigned_url(
    "PUT",
    "my-bucket",
    "my-object",
    expires=timedelta(days=1),
    response_headers={"response-content-type": "application/json"},
)
print(url)

# Get presigned URL string to download 'my-object' in
# 'my-bucket' with two hours expiry.
url = client.get_presigned_url(
    "GET",
    "my-bucket",
    "my-object",
    expires=timedelta(hours=2),
)
print(url)

upload_snowball_objects(bucket_name, object_list, metadata=None, sse=None, tags=None, retention=None, legal_hold=False, staging_filename=None, compression=False)
Uploads multiple objects in a single put call. It is done by creating intermediate TAR file optionally compressed which is uploaded to S3 service.

Parameters

Param	Type	Description
bucket_name	str	Name of the bucket.
object_list	iterable	An iterable containing :class:SnowballObject object.
metadata	dict	Any additional metadata to be uploaded along with your PUT request.
sse	Sse	Server-side encryption.
tags	Tags	Tags for the object.
retention	Retention	Retention configuration.
legal_hold	bool	Flag to set legal hold for the object.
staging_filename	str	A staging filename to create intermediate tarball.
compression	bool	Flag to compress tarball.
Return Value

Return
ObjectWriteResult object.
Example

# Upload snowball object.
client.upload_snowball_objects(
    "my-bucket",
    [
        SnowballObject("my-object1", filename="/etc/hostname"),
        SnowballObject(
            "my-object2", data=io.BytesIO("hello"), length=5,
        ),
        SnowballObject(
            "my-object3", data=io.BytesIO("world"), length=5,
            mod_time=datetime.now(),
        ),
    ],
)
5. Explore Further