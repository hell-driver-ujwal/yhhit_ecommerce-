from http import HTTPStatus


def document_json_responses(result, generator, request, public):
    error = {
        "type": "object", "required": ["error"],
        "properties": {"error": {"type": "object", "additionalProperties": True}},
        "example": {"error": {"quantity": ["Quantity exceeds available stock."]}},
    }
    result["components"]["schemas"]["ApiError"] = error
    for path, operations in result["paths"].items():
        for method, operation in operations.items():
            responses = operation["responses"]
            for response in responses.values():
                media = response.get("content", {}).get("application/json")
                if media:
                    media["schema"] = {
                        "type": "object", "required": ["data"],
                        "properties": {"data": media["schema"]},
                    }
            errors = {400, 401, 403, 500}
            if "{" in path or path == "/cart/api/items/":
                errors.add(404)
            if method == "delete" and "/category/" in path:
                errors.add(409)
            for code in errors:
                responses[str(code)] = {
                    "description": HTTPStatus(code).phrase,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiError"}}},
                }
            if method == "get" and path.startswith("/products") and operation["operationId"] != "seller_my_products":
                operation.setdefault("security", []).append({})
    return result
