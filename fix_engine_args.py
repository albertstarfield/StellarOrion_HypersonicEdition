file_path = "StellarOrionEngineMach5Up.py"
with open(file_path, "r") as f:
    content = f.read()

target = """        if default_payload:
            cmd_cad.extend(["--defaultPayload"])
            if opt_params:
                if 'payload_type' in opt_params:
                    cmd_cad.extend(["--payload_type", str(opt_params['payload_type'])])
                if 'payload_radius' in opt_params:
                    cmd_cad.extend(["--payload_radius", str(opt_params['payload_radius'])])
                if 'payload_height' in opt_params:
                    cmd_cad.extend(["--payload_height", str(opt_params['payload_height'])])
        elif payload_file:
            cmd_cad.extend(["--payload_file", payload_file])"""

replacement = """        if opt_params and 'payload_type' in opt_params:
            cmd_cad.extend(["--payload_type", str(opt_params['payload_type'])])
        if opt_params and 'payload_radius' in opt_params:
            cmd_cad.extend(["--payload_radius", str(opt_params['payload_radius'])])
        if opt_params and 'payload_height' in opt_params:
            cmd_cad.extend(["--payload_height", str(opt_params['payload_height'])])
            
        if default_payload:
            cmd_cad.extend(["--defaultPayload"])
        elif payload_file:
            cmd_cad.extend(["--payload_file", payload_file])"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed engine args!")
else:
    print("Could not find target in StellarOrionEngineMach5Up.py!")
