use pyo3::prelude::*;

mod frame;

#[pyfunction]
fn add(a: isize, b: isize) -> isize {
    a + b
}

#[pymodule]
fn videopilot_core(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(add, m)?)?;
    m.add_class::<frame::VideoFrame>()?;
    Ok(())
}
