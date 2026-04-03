use numpy::PyArray3;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

#[derive(Clone, Debug)]
#[pyclass]
pub struct VideoFrame {
    width: usize,
    height: usize,
    channels: usize,
    data: Vec<u8>,
    stride: usize,
}

#[pymethods]
impl VideoFrame {
    #[new]
    pub fn new(width: usize, height: usize, channels: usize) -> Self {
        let stride = width * channels;
        let data = vec![0u8; height * stride];

        VideoFrame {
            width,
            height,
            channels,
            data,
            stride,
        }
    }

    #[getter]
    pub fn width(&self) -> usize {
        self.width
    }

    #[getter]
    pub fn height(&self) -> usize {
        self.height
    }

    #[getter]
    pub fn channels(&self) -> usize {
        self.channels
    }

    #[getter]
    pub fn stride(&self) -> usize {
        self.stride
    }

    pub fn size_bytes(&self) -> usize {
        self.data.len()
    }
}
