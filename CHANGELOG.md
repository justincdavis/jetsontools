## 0.1.0 (06-03-2025)

### Changed

- jetsontools.info no longer entrypoint, now 'jetsontools info'
- Jetson info reads via Python now instead of using shell scripts.
- Tegrastats -> TegraStats
- TegraStats does require a file now, will use tempfile behind the scenes
- TegraStats new pattern recomended. Create object then use context manager for profiling, then access
  data property after context manager. GC cleans up object normally.
- TegraData now created from TegraStats when accessing the data via Python.

## 0.0.5 (03-27-2025)

### Fixed

- OrinNX parses power draw data correctly

## 0.0.2 (10-22-2024)

### Added

- Various parsing functions for the output of Tegrastats

### Improved

- Tegrastats now syncs start to primary thread
