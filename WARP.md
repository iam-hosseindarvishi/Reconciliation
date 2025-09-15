# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a **Bank Reconciliation System** written in Python using tkinter/ttkbootstrap for the GUI. The application helps reconcile transactions between bank data, POS (Point of Sale) data, and accounting records for Iranian banks (primarily Mellat Bank and Keshavarzi Bank). The interface supports Persian (Farsi) language with RTL text direction.

## Common Development Commands

### Environment Setup
```bash
# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate virtual environment (Windows Command Prompt)
.\.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Run the main application
python main.py

# Run in development mode with detailed logging
python main.py
```

### Testing and Data
```bash
# Create sample data for testing
python Test\Keshavarzi\create_sample_data.py

# Check current dependencies
pip freeze

# Database operations (SQLite database is automatically initialized)
# Database file location: Data\app.db
```

### Development Workflow
```bash
# Check virtual environment status
pip list

# Update a specific package
pip install --upgrade package_name

# Backup database before major changes
copy "Data\app.db" "Data\app.db.backup"
```

## Code Architecture

### High-Level Structure

The application follows a **layered architecture** with clear separation of concerns:

1. **Presentation Layer** (`ui/` directory)
   - Tab-based interface using ttkbootstrap
   - Each tab handles specific functionality (Dashboard, Data Entry, Bank Management, Reconciliation, etc.)
   - Persian language support with custom font (Vazir.ttf)

2. **Business Logic Layer** (`reconciliation/` directory)
   - Core reconciliation algorithms for different transaction types
   - Bank-specific reconciliation logic (Mellat and Keshavarzi)
   - Transaction categorization and matching algorithms

3. **Data Access Layer** (`database/` directory)
   - Repository pattern for data access
   - SQLite database with automatic initialization
   - Separate repositories for different entity types

4. **Utility Layer** (`utils/` directory)
   - Excel import/export functionality
   - Date conversion utilities (Gregorian ↔ Persian)
   - Logging configuration
   - Constants and helper functions

### Key Components

#### Database Schema
- **Banks**: Supported banks (Mellat, Keshavarzi)
- **BankTransactions**: Bank statement data
- **PosTransactions**: POS terminal transactions
- **AccountingTransactions**: Accounting system records
- **ReconciliationResults**: Matched transaction records
- **Terminals**: POS terminal information

#### Reconciliation Process
The reconciliation engine (`reconciliation/reconciliation_logic.py`) handles:
1. **Unknown Transaction Classification**: Categorizes unidentified bank transactions
2. **Automated Matching**: Matches transactions across different data sources
3. **Manual Review**: Queues ambiguous matches for user review
4. **Bank-Specific Logic**: Different algorithms for different banks

#### Transaction Types
- **POS Transactions**: Card payments through terminals
- **Bank Transfers**: Received and paid transfers
- **Checks**: Received and paid checks
- **Bank Fees**: Service charges and fees

### File Organization Patterns

- **Configuration**: `config/settings.py` - centralized app settings
- **Database Init**: `database/init_db.py` - automatic schema creation
- **UI Tabs**: Each major feature has its own tab class
- **Bank Processors**: `utils/*_bank_processor.py` - bank-specific data parsing
- **Excel Importers**: `utils/*_excel_importer.py` - data import functionality

### Persian Language Support

The application extensively supports Persian/Farsi:
- **RTL Text Direction**: Configured in settings
- **Persian Fonts**: Uses Vazir.ttf font
- **Date Conversion**: Gregorian to Persian calendar conversion
- **Number Formatting**: Persian number formatting with thousand separators

### Error Handling and Logging

- **Structured Logging**: Separate log files for different components
- **Error Recovery**: Graceful error handling in UI components
- **User Feedback**: Persian language error messages
- **File Locations**: Logs stored in `Data/` directory

## Development Guidelines

### Adding New Banks
1. Add bank constants to `utils/constants.py`
2. Create bank processor in `utils/`
3. Add reconciliation logic in `reconciliation/`
4. Update database initialization if needed

### Adding New Transaction Types
1. Update constants in `utils/constants.py`
2. Modify reconciliation logic to handle new type
3. Update UI components if user interaction needed
4. Add corresponding database fields if required

### UI Development
- Follow existing tab structure for consistency
- Use ttkbootstrap for consistent theming
- Ensure Persian language support in all UI elements
- Test with actual Persian data for proper RTL rendering

### Database Changes
- Modify `database/init_db.py` for schema changes
- Add migration logic if needed for existing databases
- Update corresponding repository classes
- Test with existing data to ensure compatibility

### Testing
- Use sample data in `Test/` directory
- Test with both banks (Mellat and Keshavarzi)
- Verify Persian text rendering and RTL layout
- Test reconciliation algorithms with edge cases

## Important Notes

- **Database Location**: SQLite database is stored in `Data/app.db`
- **Font Dependency**: Application requires Vazir.ttf font in `assets/fonts/`
- **Virtual Environment**: Always use the `.venv` virtual environment
- **Excel Compatibility**: Supports both .xlsx and .xls formats for import/export
- **Threading**: UI operations use threading to prevent interface freezing
- **Backup**: Important to backup database before major operations

## Common Issues

- **Font Rendering**: Ensure Vazir.ttf is available and properly loaded
- **Date Conversion**: Handle edge cases in Persian calendar conversion
- **Excel Import**: Validate data structure before processing
- **Memory Usage**: Monitor memory with large datasets
- **Threading**: Properly handle UI updates from background threads
