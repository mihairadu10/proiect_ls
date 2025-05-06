def add_quotes_to_lines(input_file, output_file):
    # Open the input file in read mode and the output file in write mode
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        # Iterate over each line in the input file
        for line in infile:
            # Strip any leading/trailing whitespace and add quotes
            modified_line = f'"{line.strip()}",\n'
            # Write the modified line to the output file
            outfile.write(modified_line)

    print(f"Processed lines have been written to {output_file}")

# Example usage
input_file = 'questions.txt'  # Replace with your input file
output_file = 'questions_e.txt'  # Replace with your desired output file

add_quotes_to_lines(input_file, output_file)
