import mlflow
import json
import sys

def get_model_version():
    client = mlflow.tracking.MlflowClient()
    try:
        model_name = "Race prediction"
        # Get all versions
        filter_string = f"name='{model_name}'"
        versions = client.search_model_versions(filter_string)
        
        # Set production alias on latest version if not already set
        if versions:
            latest_version = sorted(versions, key=lambda x: x.version, reverse=True)[0]
            try:
                prod_version = client.get_model_version_by_alias(model_name, "production")
            except mlflow.exceptions.RestException:
                # If no production alias exists, set it on the latest version
                client.set_registered_model_alias(model_name, "production", latest_version.version)
                prod_version = latest_version

            version_info = {
                'name': model_name,
                'version': prod_version.version,
                'run_id': prod_version.run_id,
                'creation_timestamp': prod_version.creation_timestamp
            }
            return json.dumps(version_info)
        else:
            print("No versions found", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error getting model version: {str(e)}", file=sys.stderr)
        return None

if __name__ == "__main__":
    mlflow.set_tracking_uri("http://seito.lavbic.net:5000")
    version_info = get_model_version()
    if version_info:
        print(version_info)
        sys.exit(0)
    else:
        sys.exit(1)