import sys
print("Python version:", sys.version)
print("Python path:", sys.path)

try:
    import serial
    print("Serial version:", serial.__version__)
    print("Serial path:", serial.__file__)
    print("Serial contents:", dir(serial))
    
    from serial import Serial, SerialException
    print("Successfully imported Serial and SerialException")
    print("Serial class:", Serial)
    print("SerialException class:", SerialException)
except Exception as e:
    print("Error:", str(e))

print("\nAll serial-related packages:")
import pkg_resources
for package in pkg_resources.working_set:
    if 'serial' in package.project_name.lower():
        print(package.project_name, package.version)