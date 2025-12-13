"""Prompt selection utility for terminal chat."""
import pathlib
from . import config


def select_prompt(prompt_dir=None):
    """Display a list of available prompts and let user select one.
    
    Args:
        prompt_dir: Directory to search for prompts. Uses config.PROMPT_DIR if None.
        
    Returns:
        Path to selected prompt file, or None if cancelled.
    """
    prompt_dir = prompt_dir or config.PROMPT_DIR
    prompt_path = pathlib.Path(prompt_dir)
    
    if not prompt_path.exists():
        print(f"Prompt directory not found: {prompt_dir}")
        return None
    
    # Find all .prompt.md files
    prompts = sorted(prompt_path.glob('*.prompt.md'))
    
    if not prompts:
        print(f"No prompts found in {prompt_dir}")
        return None
    
    # Display prompt list
    print("\nAvailable prompts:")
    print("-" * 50)
    for i, prompt_file in enumerate(prompts, 1):
        print(f"{i}. {prompt_file.stem.replace('.prompt', '')}")
    print("-" * 50)
    
    # Get user selection
    while True:
        try:
            choice = input("\nSelect prompt number (or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(prompts):
                selected = prompts[choice_num - 1]
                print(f"Selected: {selected.name}")
                return str(selected)
            else:
                print(f"Please enter a number between 1 and {len(prompts)}")
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None
