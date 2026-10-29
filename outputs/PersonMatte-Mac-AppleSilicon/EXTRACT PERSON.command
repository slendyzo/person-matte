#!/bin/bash
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
"$TASK_ROOT/runtime/bin/python3.13" -I -B "$TASK_ROOT/person_matte.py" "$@"
TASK_RESULT=$?
printf '\n'
if [ "$TASK_RESULT" -ne 0 ]; then
  printf 'Extraction did not complete. See the error above and README.txt.\n'
fi
read -r -p 'Press Return to close. ' TASK_REPLY
exit "$TASK_RESULT"
