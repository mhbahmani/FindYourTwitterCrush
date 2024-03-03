PRIVATE_OUTPUT_DOMAIN = "twitter-stats.mhbahmani.ir"

def generate_private_output_address(output_path) -> str:
    return f'{PRIVATE_OUTPUT_DOMAIN}/{output_path.split("/")[-1]}'