"""Export the native API contract. Run with an isolated, prepared test database."""
import json
from pathlib import Path


def contract():
    from nova.app import app
    # Do not change the web application's cached OpenAPI document in place.
    import copy
    schema=copy.deepcopy(app.openapi())
    schema['info']={'title':'Zova first-party mobile API','version':'1.0.0'}
    schema['paths']={path:value for path,value in schema['paths'].items() if path.startswith('/api/v1/')}
    schema.setdefault('components',{}).setdefault('securitySchemes',{})['nativeBearer']={'type':'http','scheme':'bearer'}
    for path,operations in schema['paths'].items():
        for operation in operations.values():
            if path not in {'/api/v1/config','/api/v1/auth/token','/api/v1/auth/refresh'}:
                operation['security']=[{'nativeBearer':[]}]
    return schema


def main():
    schema=contract()
    output=Path('docs/api/mobile-v1.openapi.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(schema,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f'Exported {len(schema["paths"])} native API paths')


if __name__=='__main__':main()
