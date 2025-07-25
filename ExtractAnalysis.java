//Custom script to extract firmware analysis results
//@category Analysis
//@author Firmware Analyst
//@menupath Analysis.Extract Firmware Analysis

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.data.*;
import java.io.PrintWriter;
import java.io.FileWriter;

public class ExtractAnalysis extends GhidraScript {

    @Override
    public void run() throws Exception {
        
        PrintWriter writer = new PrintWriter(new FileWriter("ghidra_analysis_results.txt"));
        
        // Header
        writer.println("=== GHIDRA FIRMWARE ANALYSIS RESULTS ===");
        writer.println("Program: " + currentProgram.getName());
        writer.println("Image Base: " + currentProgram.getImageBase());
        writer.println("Language: " + currentProgram.getLanguage().getLanguageID());
        writer.println("");
        
        // Functions
        writer.println("=== FUNCTIONS DISCOVERED ===");
        FunctionManager functionManager = currentProgram.getFunctionManager();
        FunctionIterator functions = functionManager.getFunctions(true);
        int functionCount = 0;
        
        while (functions.hasNext()) {
            Function function = functions.next();
            functionCount++;
            
            writer.println("Function " + functionCount + ":");
            writer.println("  Address: " + function.getEntryPoint());
            writer.println("  Name: " + function.getName());
            writer.println("  Size: " + function.getBody().getNumAddresses() + " bytes");
            
            // Get calling convention if available
            if (function.getCallingConvention() != null) {
                writer.println("  Calling Convention: " + function.getCallingConvention().getName());
            }
            
            // Get parameter count
            writer.println("  Parameters: " + function.getParameterCount());
            
            // Check if it's a thunk
            if (function.isThunk()) {
                writer.println("  Type: Thunk function");
            }
            
            writer.println("");
        }
        
        writer.println("Total Functions Found: " + functionCount);
        writer.println("");
        
        // Memory blocks
        writer.println("=== MEMORY LAYOUT ===");
        MemoryBlock[] blocks = currentProgram.getMemory().getBlocks();
        for (MemoryBlock block : blocks) {
            writer.println("Block: " + block.getName());
            writer.println("  Start: " + block.getStart());
            writer.println("  End: " + block.getEnd());
            writer.println("  Size: " + block.getSize() + " bytes");
            writer.println("  Type: " + (block.isExecute() ? "CODE" : "DATA"));
            writer.println("  Permissions: " + 
                (block.isRead() ? "R" : "-") +
                (block.isWrite() ? "W" : "-") +
                (block.isExecute() ? "X" : "-"));
            writer.println("");
        }
        
        // Symbols
        writer.println("=== SYMBOLS AND LABELS ===");
        SymbolTable symbolTable = currentProgram.getSymbolTable();
        SymbolIterator symbols = symbolTable.getAllSymbols(true);
        int symbolCount = 0;
        
        while (symbols.hasNext() && symbolCount < 50) { // Limit to first 50
            Symbol symbol = symbols.next();
            if (!symbol.getName().startsWith("LAB_") && 
                !symbol.getName().startsWith("DAT_") &&
                !symbol.getName().startsWith("PTR_")) {
                symbolCount++;
                writer.println("Symbol " + symbolCount + ":");
                writer.println("  Address: " + symbol.getAddress());
                writer.println("  Name: " + symbol.getName());
                writer.println("  Type: " + symbol.getSymbolType());
                writer.println("");
            }
        }
        
        // Strings
        writer.println("=== ASCII STRINGS FOUND ===");
        AddressSetView stringAddresses = currentProgram.getMemory().getAllInitializedAddressSet();
        DataIterator dataIterator = currentProgram.getListing().getDefinedData(stringAddresses, true);
        int stringCount = 0;
        
        while (dataIterator.hasNext() && stringCount < 100) { // Limit to first 100
            Data data = dataIterator.next();
            if (data.hasStringValue()) {
                stringCount++;
                String stringValue = data.getDefaultValueRepresentation();
                if (stringValue.length() > 4) { // Only meaningful strings
                    writer.println("String " + stringCount + ":");
                    writer.println("  Address: " + data.getAddress());
                    writer.println("  Value: " + stringValue);
                    writer.println("");
                }
            }
        }
        
        // References
        writer.println("=== CROSS REFERENCES SUMMARY ===");
        ReferenceManager refManager = currentProgram.getReferenceManager();
        AddressIterator addresses = currentProgram.getMemory().getAllInitializedAddressSet().getAddresses(true);
        int refCount = 0;
        int totalRefs = 0;
        
        while (addresses.hasNext() && refCount < 20) { // Limit output
            Address addr = addresses.next();
            Reference[] refs = refManager.getReferencesFrom(addr);
            if (refs.length > 0) {
                totalRefs += refs.length;
                refCount++;
                writer.println("From " + addr + ":");
                for (Reference ref : refs) {
                    writer.println("  -> " + ref.getToAddress() + " (" + ref.getReferenceType() + ")");
                }
                writer.println("");
            }
        }
        writer.println("Total References Analyzed: " + totalRefs);
        
        writer.close();
        println("Analysis results written to ghidra_analysis_results.txt");
    }
}
