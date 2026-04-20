# StellarOrion HypersonicEdition

This project uses a hybrid architecture for running simulations.

- **Docker:** Used exclusively for running the SPARTA simulation in a containerized Linux environment. This ensures reproducibility of the SPARTA build and execution.
- **Native OS:** The Python environment, including packages from `requirements.txt` like PyTorch, is intended to be used on the native operating system (e.g., macOS, Windows, or Linux). This allows leveraging native hardware acceleration like Apple's Metal Performance Shaders (MPS), NVIDIA CUDA, Intel oneAPI, or the CPU for pre- and post-processing tasks.

This separation allows for a flexible workflow where the computationally intensive SPARTA simulation is isolated, while data analysis and other tasks can be performed using the local machine's full capabilities.
