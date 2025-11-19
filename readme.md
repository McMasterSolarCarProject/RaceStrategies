# How to Run:

set up the venv with requirments.txt

run files with:

python -m src.engine.models

# Stuff That Needs to Be Done

## Important:
- fix update velocity file to seperate arc speed limits
- traffic.py needs to be fixed

## General:
- Add Test files for all the modules
- Fix the graphs file
- Is there a better way to do constants.py??
- Apply Input Validation for all files aswell, make sure all functions do something

## Engine:
- Models Needs to be Remade with correct motor calcs
- Need to go over Kinematics ESP and make sure all implementations are using valid classes
- Figure out math to integrate solar cell power to SOC
    ^ Implement Battery Module After Motor module is complete

## Database:
- integrate init_route_table with traffic.py
    ^ Currently has problems with the regroup function
- Parse Route Table and Parse Route Seem Pretty Good
- Why are there multiple parse_route files? Rename things to make them make more sense
- init_route_table gotta be remade so its more modular


# File Structure:

# src: - All the code thats run to do stuff
## - Database:
    - init_route_table -> initializes the database
    Finish ts after remaking the file structure


