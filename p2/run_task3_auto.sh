#!/bin/bash

# Task 3: Testing Loss Probability
# IMPORTANT: You must manually restart the server with different p values
# Server command: python server_auto.py 7735 received.txt <p-value>

SERVER="152.7.178.180"
N=64
MSS=500

echo "Task 3: Testing Loss Probability with Auto-Reset Server"
echo "Fixed parameters: N=$N, MSS=$MSS"
echo ""

echo "p,Run1,Run2,Run3,Run4,Run5,Average" > task3_results.csv

for p in 0.01 0.02 0.03 0.04 0.05 0.06 0.07 0.08 0.09 0.10
do
    echo ""
    echo "========================================"
    echo "Testing p=$p"
    echo "========================================"
    echo ""
    echo "*** RESTART SERVER WITH p=$p ***"
    echo "On server: Ctrl+C, then run:"
    echo "python server_auto.py 7735 received.txt $p"
    echo ""
    read -p "Press Enter when server is ready with p=$p..."
    
    echo -n "$p," >> task3_results.csv
    
    times=()
    
    for trial in 1 2 3 4 5
    do
        echo "  Trial $trial/5..."
        
        # Run client and capture output
        output=$(python3 client.py $SERVER 7735 test_1mb.txt $N $MSS 2>&1)
        
        # Extract time
        time=$(echo "$output" | grep "Done!" | grep -oE '[0-9]+\.[0-9]+' | head -1)
        
        if [ -z "$time" ]; then
            echo "    ERROR: Could not extract time!"
            time="ERROR"
        else
            echo "    Time: ${time}s"
            times+=($time)
        fi
        
        # Save to CSV
        echo -n "$time" >> task3_results.csv
        if [ $trial -lt 5 ]; then
            echo -n "," >> task3_results.csv
        fi
        
        # Wait for server to reset (5 second timeout + 1 second buffer)
        echo "    Waiting for server to reset..."
        sleep 6
    done
    
    # Calculate average
    if [ ${#times[@]} -eq 5 ]; then
        avg=$(echo "${times[@]}" | awk '{sum=0; for(i=1;i<=NF;i++) sum+=$i; print sum/NF}')
        echo -n ",$avg" >> task3_results.csv
        echo "  Average: ${avg}s"
    else
        echo -n ",ERROR" >> task3_results.csv
    fi
    
    echo "" >> task3_results.csv
    echo "p=$p complete!"
done

echo ""
echo "========================================"
echo "All tests complete!"
echo "Results saved to task3_results.csv"
echo "========================================"
