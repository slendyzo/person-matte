#!/bin/bash
set -o pipefail
TASK_ROOT="$(cd -- "$(dirname "$0")" && pwd -P)"
TASK_ARCH=$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null)
TASK_OS=$(/usr/bin/sw_vers -productVersion)
TASK_MAJOR=${TASK_OS%%.*}
TASK_MINOR=${TASK_OS#*.}
TASK_MINOR=${TASK_MINOR%%.*}
if [ "$TASK_ARCH" != "1" ] || [ "$TASK_MAJOR" -lt 13 ] || { [ "$TASK_MAJOR" -eq 13 ] && [ "$TASK_MINOR" -lt 4 ]; }; then
  printf '\nThis package requires an Apple-silicon Mac with macOS 13.4 or newer.\n'
  read -r -p 'Press Return to close. ' TASK_REPLY
  exit 1
fi
{
  printf 'Person Matte / Apple silicon / macOS %s\n' "$TASK_OS"
  "$TASK_ROOT/runtime/bin/python3.13" -I -B "$TASK_ROOT/person_matte.py" --check
} 2>&1 | /usr/bin/tee "$TASK_ROOT/CHECK-RESULT.txt"
TASK_RESULT=$?
printf '\nThe check output is saved as CHECK-RESULT.txt.\n'
read -r -p 'Press Return to close. ' TASK_REPLY
exit "$TASK_RESULT"
