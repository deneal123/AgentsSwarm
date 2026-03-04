Prerequisites
Ensure you have the following prerequisites before proceeding:

Docker installed on your machine
Install tritonclient:

pip install tritonclient[all]
Exporting YOLO26 to ONNX Format
Before deploying the model on Triton, it must be exported to the ONNX format. ONNX (Open Neural Network Exchange) is a format that allows models to be transferred between different deep learning frameworks. Use the export function from the YOLO class:


from ultralytics import YOLO

# Load a model
model = YOLO("yolo26n.pt")  # load an official model

# Retrieve metadata during export. Metadata needs to be added to config.pbtxt. See next section.
metadata = []


def export_cb(exporter):
    metadata.append(exporter.metadata)


model.add_callback("on_export_end", export_cb)

# Export the model
onnx_file = model.export(format="onnx", dynamic=True)
Setting Up Triton Model Repository
The Triton Model Repository is a storage location where Triton can access and load models.

Create the necessary directory structure:


from pathlib import Path

# Define paths
model_name = "yolo"
triton_repo_path = Path("tmp") / "triton_repo"
triton_model_path = triton_repo_path / model_name

# Create directories
(triton_model_path / "1").mkdir(parents=True, exist_ok=True)
Move the exported ONNX model to the Triton repository:


from pathlib import Path

# Move ONNX model to Triton Model path
Path(onnx_file).rename(triton_model_path / "1" / "model.onnx")

# Create config file
(triton_model_path / "config.pbtxt").touch()

data = """
# Add metadata
parameters {
  key: "metadata"
  value {
    string_value: "%s"
  }
}

# (Optional) Enable TensorRT for GPU inference
# First run will be slow due to TensorRT engine conversion
optimization {
  execution_accelerators {
    gpu_execution_accelerator {
      name: "tensorrt"
      parameters {
        key: "precision_mode"
        value: "FP16"
      }
      parameters {
        key: "max_workspace_size_bytes"
        value: "3221225472"
      }
      parameters {
        key: "trt_engine_cache_enable"
        value: "1"
      }
      parameters {
        key: "trt_engine_cache_path"
        value: "/models/yolo/1"
      }
    }
  }
}
""" % metadata[0]  # noqa

with open(triton_model_path / "config.pbtxt", "w") as f:
    f.write(data)
Running Triton Inference Server
Run the Triton Inference Server using Docker:


import contextlib
import subprocess
import time

from tritonclient.http import InferenceServerClient

# Define image https://catalog.ngc.nvidia.com/orgs/nvidia/containers/tritonserver
tag = "nvcr.io/nvidia/tritonserver:24.09-py3"  # 8.57 GB

# Pull the image
subprocess.call(f"docker pull {tag}", shell=True)

# Run the Triton server and capture the container ID
container_id = (
    subprocess.check_output(
        f"docker run -d --rm --runtime=nvidia --gpus 0 -v {triton_repo_path}:/models -p 8000:8000 {tag} tritonserver --model-repository=/models",
        shell=True,
    )
    .decode("utf-8")
    .strip()
)

# Wait for the Triton server to start
triton_client = InferenceServerClient(url="localhost:8000", verbose=False, ssl=False)

# Wait until model is ready
for _ in range(10):
    with contextlib.suppress(Exception):
        assert triton_client.is_model_ready(model_name)
        break
    time.sleep(1)
Then run inference using the Triton Server model:


from ultralytics import YOLO

# Load the Triton Server model
model = YOLO("http://localhost:8000/yolo", task="detect")

# Run inference on the server
results = model("path/to/image.jpg")
Cleanup the container:


# Kill and remove the container at the end of the test
subprocess.call(f"docker kill {container_id}", shell=True)
TensorRT Optimization (Optional)
For even greater performance, you can use TensorRT with Triton Inference Server. TensorRT is a high-performance deep learning optimizer built specifically for NVIDIA GPUs that can significantly increase inference speed.

Key benefits of using TensorRT with Triton include:

Up to 36x faster inference compared to unoptimized models
Hardware-specific optimizations for maximum GPU utilization
Support for reduced precision formats (INT8, FP16) while maintaining accuracy
Layer fusion to reduce computational overhead
To use TensorRT directly, you can export your YOLO26 model to TensorRT format:


from ultralytics import YOLO

# Load the YOLO26 model
model = YOLO("yolo26n.pt")

# Export the model to TensorRT format
model.export(format="engine")  # creates 'yolo26n.engine'
For more information on TensorRT optimization, see the TensorRT integration guide.