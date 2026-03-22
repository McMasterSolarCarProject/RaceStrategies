import sys
from .main import main as run_asc_main
from .optimize_fsgp import main as run_fsgp_main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "fsgp":
        print("Running FSGP track optimization...")
        
        # Parse optional parameters
        kwargs = {}
        for arg in sys.argv[2:]:
            if "=" in arg:
                key, value = arg.split("=", 1)
                # Try to convert to appropriate type
                if value.isdigit():
                    kwargs[key] = int(value)
                elif value.lower() in ('true', 'false'):
                    kwargs[key] = value.lower() == 'true'
                else:
                    try:
                        kwargs[key] = float(value)
                    except ValueError:
                        kwargs[key] = value
        
        run_fsgp_main(**kwargs)
    else:
        print("Running ASC_2024 main module...")
        print("(Use 'python -m src fsgp' to run FSGP optimization instead)")
        print("(Use 'python -m src fsgp generations=150 pop_size=80' to customize parameters)")
        run_asc_main()