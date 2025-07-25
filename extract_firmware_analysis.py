# Extract detailed firmware analysis results from Ghidra
# @author Firmware Analyst
# @category Analysis
# @menupath Analysis.Extract Firmware Results

# Write results to a file
output_file = open("ghidra_firmware_results.txt", "w")

# Header
output_file.write("=== GHIDRA FIRMWARE ANALYSIS RESULTS ===\\n")
output_file.write("Program: {}\\n".format(currentProgram.getName()))
output_file.write("Image Base: {}\\n".format(currentProgram.getImageBase()))
output_file.write("Language: {}\\n".format(currentProgram.getLanguage().getLanguageID()))
output_file.write("\\n")

# Functions
output_file.write("=== FUNCTIONS DISCOVERED ===\\n")
function_manager = currentProgram.getFunctionManager()
functions = function_manager.getFunctions(True)
function_count = 0

for function in functions:
    function_count += 1
    output_file.write("Function {}:\\n".format(function_count))
    output_file.write("  Address: {}\\n".format(function.getEntryPoint()))
    output_file.write("  Name: {}\\n".format(function.getName()))
    output_file.write("  Size: {} bytes\\n".format(function.getBody().getNumAddresses()))
    
    # Get parameter count
    output_file.write("  Parameters: {}\\n".format(function.getParameterCount()))
    
    # Check if it's a thunk
    if function.isThunk():
        output_file.write("  Type: Thunk function\\n")
    
    output_file.write("\\n")

output_file.write("Total Functions Found: {}\\n".format(function_count))
output_file.write("\\n")

# Memory blocks
output_file.write("=== MEMORY LAYOUT ===\\n")
memory = currentProgram.getMemory()
blocks = memory.getBlocks()

for block in blocks:
    output_file.write("Block: {}\\n".format(block.getName()))
    output_file.write("  Start: {}\\n".format(block.getStart()))
    output_file.write("  End: {}\\n".format(block.getEnd()))
    output_file.write("  Size: {} bytes\\n".format(block.getSize()))
    output_file.write("  Type: {}\\n".format("CODE" if block.isExecute() else "DATA"))
    perms = ""
    perms += "R" if block.isRead() else "-"
    perms += "W" if block.isWrite() else "-"
    perms += "X" if block.isExecute() else "-"
    output_file.write("  Permissions: {}\\n".format(perms))
    output_file.write("\\n")

# Symbols (limit to avoid huge output)
output_file.write("=== SYMBOLS AND LABELS ===\\n")
symbol_table = currentProgram.getSymbolTable()
symbols = symbol_table.getAllSymbols(True)
symbol_count = 0

for symbol in symbols:
    if symbol_count >= 50:  # Limit output
        break
    name = symbol.getName()
    if not (name.startswith("LAB_") or name.startswith("DAT_") or name.startswith("PTR_")):
        symbol_count += 1
        output_file.write("Symbol {}:\\n".format(symbol_count))
        output_file.write("  Address: {}\\n".format(symbol.getAddress()))
        output_file.write("  Name: {}\\n".format(name))
        output_file.write("  Type: {}\\n".format(symbol.getSymbolType()))
        output_file.write("\\n")

# Strings (limit to meaningful ones)
output_file.write("=== ASCII STRINGS FOUND ===\\n")
listing = currentProgram.getListing()
memory_set = currentProgram.getMemory().getAllInitializedAddressSet()
data_iterator = listing.getDefinedData(memory_set, True)
string_count = 0

for data in data_iterator:
    if string_count >= 100:  # Limit output
        break
    if data.hasStringValue():
        string_value = str(data.getDefaultValueRepresentation())
        if len(string_value) > 6:  # Only meaningful strings
            string_count += 1
            output_file.write("String {}:\\n".format(string_count))
            output_file.write("  Address: {}\\n".format(data.getAddress()))
            output_file.write("  Value: {}\\n".format(string_value))
            output_file.write("\\n")

# References summary
output_file.write("=== CROSS REFERENCES SUMMARY ===\\n")
reference_manager = currentProgram.getReferenceManager()
addresses = currentProgram.getMemory().getAllInitializedAddressSet().getAddresses(True)
ref_count = 0
total_refs = 0

for addr in addresses:
    if ref_count >= 30:  # Limit output
        break
    refs = reference_manager.getReferencesFrom(addr)
    if len(refs) > 0:
        total_refs += len(refs)
        ref_count += 1
        output_file.write("From {}:\\n".format(addr))
        for ref in refs:
            output_file.write("  -> {} ({})\\n".format(ref.getToAddress(), ref.getReferenceType()))
        output_file.write("\\n")

output_file.write("Total References Analyzed: {}\\n".format(total_refs))

output_file.close()
print("Analysis results written to ghidra_firmware_results.txt")
