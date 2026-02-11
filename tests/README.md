# Ramses-Review Test Suite

Comprehensive test coverage for all Ramses-Review functionality.

## Test Statistics

- **Total Tests:** 52
- **Test Files:** 6
- **Coverage:** Core functionality, edge cases, integration workflows

## Test Modules

### 1. test_scanner.py (12 tests)
Tests preview file scanning and filtering:
- ✓ Scans project structure and finds all previews
- ✓ Parses preview filenames correctly (project, shot, step extraction)
- ✓ Detects marker files and determines status
- ✓ Handles multiple markers (uses most recent)
- ✓ Compares timestamps to detect updated previews
- ✓ Filters by date range (Today, This Week, This Month)
- ✓ Filters by sequence and step
- ✓ Handles empty projects and invalid filenames

### 2. test_tracker.py (7 tests)
Tests upload tracking and marker management:
- ✓ Creates marker files with metadata
- ✓ Reads marker file content
- ✓ Appends to history log
- ✓ Retrieves upload history for specific shots
- ✓ Marks multiple previews as sent in batch
- ✓ Handles markers with/without notes
- ✓ Handles permissions errors gracefully

### 3. test_collector.py (10 tests)
Tests file collection and shot list generation:
- ✓ Collects files successfully
- ✓ Progress callback tracking
- ✓ Cancellation support during collection
- ✓ Handles missing source files
- ✓ Creates destination folders automatically
- ✓ Generates shot list with proper formatting
- ✓ Groups shots by sequence
- ✓ Shows file sizes in shot list
- ✓ Saves shot list to file
- ✓ Handles empty collections

### 4. test_models.py (9 tests)
Tests data model integrity:
- ✓ Display name generation
- ✓ File size conversion to MB
- ✓ is_ready logic for all status types (Ready, Ready (Updated), Sent)
- ✓ Marker metadata storage
- ✓ Different video formats (mp4, mov, avi)
- ✓ Optional sequence IDs
- ✓ Datetime handling

### 5. test_config.py (9 tests)
Tests configuration management:
- ✓ Default configuration structure
- ✓ Creates default config if not exists
- ✓ Saves and loads configuration
- ✓ Loads Ramses common settings
- ✓ Saves Ramses settings (clientPath, clientPort)
- ✓ Preserves other keys when updating
- ✓ Creates config directories
- ✓ Handles corrupted config files
- ✓ Merges partial configs

### 6. test_integration.py (5 tests)
End-to-end workflow tests:
- ✓ Complete workflow: scan → collect → mark as sent
- ✓ Updated preview detection and re-upload
- ✓ Filtering workflow
- ✓ Cancellation mid-workflow
- ✓ Smart defaults (auto-select ready items)

## Running Tests

### All Tests
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Individual Test Modules
```bash
python -m unittest tests.test_scanner -v
python -m unittest tests.test_tracker -v
python -m unittest tests.test_collector -v
python -m unittest tests.test_models -v
python -m unittest tests.test_config -v
python -m unittest tests.test_integration -v
```

### Specific Test
```bash
python -m unittest tests.test_scanner.TestPreviewScanner.test_scan_finds_all_previews -v
```

## Test Coverage Areas

### Core Functionality
- Preview scanning and parsing
- Marker file creation and detection
- File collection with progress tracking
- Shot list generation
- Upload history tracking

### Edge Cases
- Empty projects
- Invalid filenames
- Missing files
- Multiple markers
- Corrupted configs
- Permissions errors
- Timestamp comparisons

### Integration
- Complete workflows
- Update cycles
- Filtering combinations
- Cancellation handling
- Smart defaults

### Bug Prevention
- ✓ Multiple marker files (uses most recent)
- ✓ Updated preview detection (timestamp comparison)
- ✓ Missing file tracking
- ✓ Cancellation support
- ✓ Cross-platform compatibility

## No "Alibi" Tests

All tests are substantive and test actual functionality:
- **Real file operations**: Uses tempfile for actual I/O
- **Timestamp logic**: Tests actual file modification time comparisons
- **Error handling**: Tests real error scenarios (permissions, missing files)
- **Integration**: Tests complete workflows, not isolated functions
- **Edge cases**: Tests boundary conditions and error paths

## Test Quality Guidelines

1. **Setup/Teardown**: Every test cleans up temp files
2. **Independence**: Tests don't depend on each other
3. **Assertions**: Multiple assertions verify complete behavior
4. **Realistic Data**: Uses actual Ramses naming conventions
5. **Error Paths**: Tests both success and failure scenarios

## Cross-Tool Integration

See `../tests/test_complete_pipeline.py` for end-to-end tests across:
- Ramses-Ingest (media ingestion)
- Ramses-Fusion (preview rendering)
- Ramses-Review (review collection)
