from minio import Minio
from minio.error import S3Error

class MinioUploader:
    def __init__(self, minio_host, minio_access, minio_secret) -> None:
        self.client = Minio(
            minio_host,
            access_key=minio_access,
            secret_key=minio_secret,
            secure=False
        )

    def upload(self, minio_bucket, minio_log_folder, file):
        found = self.client.bucket_exists(minio_bucket)
        if not found:
            self.client.make_bucket(minio_bucket)
            print("============Create bucket '{}'".format(minio_bucket))
        minio_file = minio_log_folder + '/' + file.split('/')[-1]
        self.client.fput_object(
            minio_bucket, minio_file, file,
        )
        print('Uploaded ', minio_file)


# if __name__ == "__main__":
#     try:
#         main()
#     except S3Error as exc:
#         print("error occurred.", exc)
