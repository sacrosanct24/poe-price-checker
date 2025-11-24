"""
Quick test script for the Rare Evaluation Config Window.

Run this to manually test the configuration UI.
"""

import tkinter as tk
from pathlib import Path
from gui.rare_evaluation_config_window import RareEvaluationConfigWindow


def test_config_window():
    """Test the rare evaluation config window."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    data_dir = Path(__file__).parent / "data"
    
    def on_save():
        print("✓ Save callback triggered!")
        print("  Config should be reloaded now")
    
    # Create the config window
    config_window = RareEvaluationConfigWindow(
        master=root,
        data_dir=data_dir,
        on_save_callback=on_save
    )
    
    print("Config window opened successfully!")
    print("\nInstructions:")
    print("1. Try adjusting some affix weights using the sliders")
    print("2. Change minimum value thresholds")
    print("3. Switch to the 'Presets' tab")
    print("4. Try clicking a preset button (e.g., 'Life/Res Tank')")
    print("5. Click 'Save' to test the save functionality")
    print("6. Check that data/valuable_affixes.json was updated")
    print("\nClose the window when done testing.")
    
    root.mainloop()


if __name__ == "__main__":
    test_config_window()
