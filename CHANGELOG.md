## Unreleased

### Added

- Python 3.15 support
- TegraStats.window marks named blocks of code, TegraData.window gets the data collected in one, TegraData.duration
- TegraStats read_sysfs_dla, read_sysfs_gpu, read_sysfs_pva and read_sysfs_media flags, and SysfsReader for any sysfs file, sampled without sudo in a separate process; TegraData.sysfs_counters and sysfs_gauges; get_dla_active_time
- TegraData.dla_utilization and get_dla_utilization, NVDLA utilization reported by tegrastats with sudo
- TegraStats read_sysfs_power flag samples the INA3221 power rails within an I2C read budget shared with tegrastats, TegraData.sysfs_energy integrates their energy

### Fixed

- TegraStats on Python 3.14+

## 0.1.1 (06-18-2025)

### Added

- TegraData.save_as_csv
- cli, profile command
- JetsonInfo board name, memory size, memory bitrate

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
