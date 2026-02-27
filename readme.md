# How to Run:

set up the python venv with requirments.txt

setup database by running:
```bash
python -m src.database
```

run sim with:

```bash
python -m src
```
run gui with:
```bash
streamlit run src/streamlit_app.py
```

modify database setup in database.__main__.py
modify sim setup in src.main.py

# Stuff That Needs to Be Done
## General:
- Add Test files for all the modules
- Fix the graphs file
- Is there a better way to do constants.py??
- Apply Input Validation for all files aswell, make sure all functions do something

## Engine:
- Need to go over Kinematics ESP and make sure all implementations are using valid classes
- Figure out math to integrate solar cell power to SOC
    ^ Implement Battery Module After Motor module is complete
- Make acceleration based on max torque based on motor speed
- Complete Reverse Nodes, add to control logic
- Make sure algorithm takes care of weird cases (negative eff speed)

## Database:
- Why are there multiple parse_route files? Rename things to make them make more sense
- init_route_table gotta be remade so its more modular

## Utils:
 - Create a config type python module which takes some json files with a bunch of sim configs

