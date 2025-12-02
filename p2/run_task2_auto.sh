#!/bin/bash

# Task 2: Testing MSS with auto-reset server
# One-time setup on server: python server_auto.py 7735 received.txt 0.05
# Then run this script on your laptop

SERVER="152.7.178.180"
N=64

echo "Task 2: Testing MSS with Auto-Reset Server"
echo "Fixed parameters: N=$N, p=0.05"
echo "Make sure server_auto.py is running on $SERVER"
echo ""
read -p "Press Enter to start tests..."

echo "MSS,Run1,Run2,Run3,Run4,Run5,Average" > task2_results.csv

for MSS in 100 200 300 400 500 600 700 800 900 1000
do
    echo ""
    echo "========================================"
    echo "Testing MSS=$MSS"
    echo "========================================"
    echo -n "$MSS," >> task2_results.csv
    
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
        echo -n "$time" >> task2_results.csv
        if [ $trial -lt 5 ]; then
            echo -n "," >> task2_results.csv
        fi
        
        # Wait for server to reset (5 second timeout + 1 second buffer)
        echo "    Waiting for server to reset..."
        sleep 6
    done
    
    # Calculate average
    if [ ${#times[@]} -eq 5 ]; then
        avg=$(echo "${times[@]}" | awk '{sum=0; for(i=1;i<=NF;i++) sum+=$i; print sum/NF}')
        echo -n ",$avg" >> task2_results.csv
        echo "  Average: ${avg}s"
    else
        echo -n ",ERROR" >> task2_results.csv
    fi
    
    echo "" >> task2_results.csv
    echo "MSS=$MSS complete!"
done

echo ""
echo "========================================"
echo "All tests complete!"
echo "Results saved to task2_results.csv"
echo "========================================"
