import mlflow
import json
import sys

def get_model_version():
    client = mlflow.tracking.MlflowClient()
    try:
        # Get the production version of the model
        model_name = "Race prediction"
        filter_string = "name='{}'".format(model_name)
        versions = client.search_model_versions(filter_string)
        
        # Find the production version
        prod_version = None
        for version in versions:
            if version.current_stage == 'Production':
                prod_version = version
                break
        
        if prod_version:
            # Return relevant version info as JSON
            version_info = {
                'name': model_name,
                'version': prod_version.version,
                'run_id': prod_version.run_id,
                'current_stage': prod_version.current_stage,
                'creation_timestamp': prod_version.creation_timestamp
            }
            return json.dumps(version_info)
        else:
            print("No production version found", file=sys.stderr)
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