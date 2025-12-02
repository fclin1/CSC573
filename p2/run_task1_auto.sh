#!/bin/bash

# Task 1: Automated testing with auto-reset server
# One-time setup on server: python server_auto.py 7735 received.txt 0.05
# Then run this script on your laptop

SERVER="152.7.178.180"
MSS=500

echo "Task 1: Testing Window Sizes with Auto-Reset Server"
echo "Make sure server_auto.py is running on $SERVER"
echo ""
read -p "Press Enter to start tests..."

echo "N,Run1,Run2,Run3,Run4,Run5,Average" > task1_results.csv

for N in 1 2 4 8 16 32 64 128 256 512 1024
do
    echo ""
    echo "========================================"
    echo "Testing N=$N"
    echo "========================================"
    echo -n "$N," >> task1_results.csv
    
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
        echo -n "$time" >> task1_results.csv
        if [ $trial -lt 5 ]; then
            echo -n "," >> task1_results.csv
        fi
        
        # Wait for server to reset (5 second timeout + 1 second buffer)
        echo "    Waiting for server to reset..."
        sleep 6
    done
    
    # Calculate average
    if [ ${#times[@]} -eq 5 ]; then
        avg=$(echo "${times[@]}" | awk '{sum=0; for(i=1;i<=NF;i++) sum+=$i; print sum/NF}')
        echo -n ",$avg" >> task1_results.csv
        echo "  Average: ${avg}s"
    else
        echo -n ",ERROR" >> task1_results.csv
    fi
    
    echo "" >> task1_results.csv
    echo "N=$N complete!"
done

echo ""
echo "========================================"
echo "All tests complete!"
echo "Results saved to task1_results.csv"
echo "========================================"
