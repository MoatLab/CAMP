#!/bin/bash
RUNDIR=$(echo "$(dirname "$PWD")")
source $RUNDIR/config.sh || exit

echo "setting all cores online ..."
bring_all_cpus_online

if [[ $# != 4 ]]; then
	echo "Usage: sudo ./mod-uncore-freq.sh [node0-min] [node0-max] [node1-min] [node1-max]"
	exit
fi

ZERO_MIN_UNCORE_FREQ=$1
ZERO_MAX_UNCORE_FREQ=$2
ONE_MIN_UNCORE_FREQ=$3
ONE_MAX_UNCORE_FREQ=$4

# Base directory for intel uncore frequency
UNCORE_BASE_DIR="/sys/devices/system/cpu/intel_uncore_frequency"

# Function to detect available package/die directories
detect_uncore_dirs() {
	if [[ ! -d "$UNCORE_BASE_DIR" ]]; then
		echo "Error: Intel uncore frequency directory not found at $UNCORE_BASE_DIR"
		exit 1
	fi
	
	# Find package_00_die_* directory (should be consistent across versions)
	PACKAGE_00_DIR=$(find "$UNCORE_BASE_DIR" -maxdepth 1 -name "package_00_die_*" -type d | head -1)
	if [[ -z "$PACKAGE_00_DIR" ]]; then
		echo "Error: Could not find package_00_die_* directory"
		exit 1
	fi
	
	# Find package_01_die_* directory (this varies between kernel versions)
	PACKAGE_01_DIR=$(find "$UNCORE_BASE_DIR" -maxdepth 1 -name "package_01_die_*" -type d | head -1)
	if [[ -z "$PACKAGE_01_DIR" ]]; then
		echo "Error: Could not find package_01_die_* directory"
		echo "Available directories:"
		ls -la "$UNCORE_BASE_DIR"
		exit 1
	fi
	
	echo "Detected uncore frequency directories:"
	echo "  Node 0 (Package 0): $(basename $PACKAGE_00_DIR)"
	echo "  Node 1 (Package 1): $(basename $PACKAGE_01_DIR)"
}

# Generic function to change uncore frequency
# Usage: change_uncore_freq <node> <freq_type> <frequency>
# node: 0 or 1
# freq_type: "min" or "max"
# frequency: target frequency in kHz
change_uncore_freq()
{
	local node=$1
	local freq_type=$2
	local freq=$3
	
	# Validate arguments
	if [[ ! "$node" =~ ^[01]$ ]]; then
		echo "Error: Invalid node '$node'. Must be 0 or 1."
		return 1
	fi
	
	if [[ ! "$freq_type" =~ ^(min|max)$ ]]; then
		echo "Error: Invalid frequency type '$freq_type'. Must be 'min' or 'max'."
		return 1
	fi
	
	if [[ ! "$freq" =~ ^[0-9]+$ ]]; then
		echo "Error: Invalid frequency '$freq'. Must be a positive integer."
		return 1
	fi
	
	# Select the appropriate directory
	local package_dir
	if [[ $node == 0 ]]; then
		package_dir="$PACKAGE_00_DIR"
	else
		package_dir="$PACKAGE_01_DIR"
	fi
	
	# Construct the file path
	local freq_file="$package_dir/${freq_type}_freq_khz"
	
	# Check if the file exists
	if [[ ! -f "$freq_file" ]]; then
		echo "Error: Frequency file not found: $freq_file"
		return 1
	fi
	
	# Read current frequency
	local curfreq=$(cat "$freq_file")
	
	# Set new frequency
	if ! echo $freq > "$freq_file" 2>/dev/null; then
		echo "Error: Failed to write frequency $freq to $freq_file"
		return 1
	fi
	
	# Verify the change
	local newfreq=$(cat "$freq_file")
	if [[ $freq == $newfreq ]]; then
		echo "Success! Node $node $freq_type uncore frequency has been set to $newfreq kHz"
		return 0
	else
		echo "Fail! Node $node $freq_type uncore frequency: $newfreq kHz (expected: $freq kHz)"
		return 1
	fi
}

main()
{
	# First detect the correct directories for this kernel version
	detect_uncore_dirs
	
	# Then perform the frequency changes using the generic function
	local exit_code=0
	
	change_uncore_freq 0 "min" "$ZERO_MIN_UNCORE_FREQ" || exit_code=1
	change_uncore_freq 0 "max" "$ZERO_MAX_UNCORE_FREQ" || exit_code=1
	change_uncore_freq 1 "min" "$ONE_MIN_UNCORE_FREQ" || exit_code=1
	change_uncore_freq 1 "max" "$ONE_MAX_UNCORE_FREQ" || exit_code=1
	
	return $exit_code
}

main

if [[ $? -ne 0 ]]; then
	echo "Some frequency changes failed!"
	exit 1
fi

echo "./mod-uncore-freq.sh DONE"
exit
