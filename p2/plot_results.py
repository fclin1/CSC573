#!/usr/bin/env python3
"""
Generate plots for CSC573 Project 2
"""

import matplotlib.pyplot as plt
import csv

def read_csv_data(filename):
    """Read CSV and return x values, averages"""
    x_values = []
    averages = []
    
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            x_values.append(float(list(row.values())[0]))  # First column
            avg = row.get('Average', '')
            if avg and avg != 'ERROR':
                averages.append(float(avg))
            else:
                averages.append(None)
    
    return x_values, averages

# Create figure with 3 subplots
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))

# Task 1: Window Size
try:
    n_values, task1_avg = read_csv_data('task1_results.csv')
    ax1.plot(n_values, task1_avg, 'bo-', linewidth=2, markersize=8)
    ax1.set_xlabel('Window Size (N)', fontsize=12)
    ax1.set_ylabel('Average Delay (seconds)', fontsize=12)
    ax1.set_title('Task 1: Effect of Window Size\n(MSS=500, p=0.05)', fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale('log', base=2)
except Exception as e:
    ax1.text(0.5, 0.5, f'Error loading Task 1 data:\n{e}', 
             ha='center', va='center', transform=ax1.transAxes)

# Task 2: MSS
try:
    mss_values, task2_avg = read_csv_data('task2_results.csv')
    ax2.plot(mss_values, task2_avg, 'go-', linewidth=2, markersize=8)
    ax2.set_xlabel('Maximum Segment Size (bytes)', fontsize=12)
    ax2.set_ylabel('Average Delay (seconds)', fontsize=12)
    ax2.set_title('Task 2: Effect of MSS\n(N=64, p=0.05)', fontsize=14)
    ax2.grid(True, alpha=0.3)
except Exception as e:
    ax2.text(0.5, 0.5, f'Error loading Task 2 data:\n{e}', 
             ha='center', va='center', transform=ax2.transAxes)

# Task 3: Loss Probability
try:
    p_values, task3_avg = read_csv_data('task3_results.csv')
    ax3.plot(p_values, task3_avg, 'ro-', linewidth=2, markersize=8)
    ax3.set_xlabel('Loss Probability (p)', fontsize=12)
    ax3.set_ylabel('Average Delay (seconds)', fontsize=12)
    ax3.set_title('Task 3: Effect of Loss Probability\n(N=64, MSS=500)', fontsize=14)
    ax3.grid(True, alpha=0.3)
except Exception as e:
    ax3.text(0.5, 0.5, f'Error loading Task 3 data:\n{e}', 
             ha='center', va='center', transform=ax3.transAxes)

plt.tight_layout()
plt.savefig('project2_results.png', dpi=300, bbox_inches='tight')
print("Plot saved as 'project2_results.png'")

# Also save individual plots
for i, (ax, title) in enumerate([(ax1, 'task1'), (ax2, 'task2'), (ax3, 'task3')]):
    fig_single = plt.figure(figsize=(8, 6))
    ax_new = fig_single.add_subplot(111)
    
    # Copy the plot
    for line in ax.get_lines():
        ax_new.plot(line.get_xdata(), line.get_ydata(), 
                   line.get_marker() + line.get_linestyle(), 
                   color=line.get_color(), linewidth=2, markersize=8)
    
    ax_new.set_xlabel(ax.get_xlabel(), fontsize=12)
    ax_new.set_ylabel(ax.get_ylabel(), fontsize=12)
    ax_new.set_title(ax.get_title(), fontsize=14)
    ax_new.grid(True, alpha=0.3)
    if ax.get_xscale() == 'log':
        ax_new.set_xscale('log', base=2)
    
    plt.tight_layout()
    plt.savefig(f'{title}_plot.png', dpi=300, bbox_inches='tight')
    print(f"Plot saved as '{title}_plot.png'")
    plt.close()

plt.show()
