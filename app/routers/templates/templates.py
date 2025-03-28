from fastapi import APIRouter, HTTPException, Request
from app.helpers import templates, users
from app.models.template import TemplateInDB, CreateTemplate, UpdateTemplate
from typing import List, Dict

router = APIRouter()


@router.get("", status_code=200)
async def get_all_templates(request: Request) -> Dict[str, List[TemplateInDB]]:
    """
    Retrieves all templates for the current user.

    Args:
    - request (Request): The incoming request.

    Returns:
    - Dict[str, List[TemplateInDB]]: A dictionary containing the user's templates.

    Raises:
    - HTTPException: If an error occurs while retrieving templates.
    """
    user_id = request.state.current_user.id
    response = templates.get_all_templates(user_id)
    if response is None:
        raise HTTPException(status_code=500, detail="Error getting templates")
    return response


@router.post("", status_code=201)
async def create_template(template: CreateTemplate) -> TemplateInDB:
    """
    Creates a new template.

    Args:
    - template (CreateTemplate): The template to be created.

    Returns:
    - TemplateInDB: The newly created template.

    Raises:
    - HTTPException: If the user is not found or an error occurs while creating the template.
    """
    if template.user_id is not None:
        user = users.get_user_by_id(template.user_id)
        if user is None:
            raise HTTPException(status_code=400, detail="User not found")
    response = templates.create_template(template)
    if response is None:
        raise HTTPException(status_code=500, detail="Error creating template")
    return response


@router.put("/{id}", status_code=200)
async def update_template(id: int, template: UpdateTemplate) -> TemplateInDB:
    """
    Updates an existing template.

    Args:
    - id (int): The ID of the template to be updated.
    - template (UpdateTemplate): The updated template.

    Returns:
    - TemplateInDB: The updated template.

    Raises:
    - HTTPException: If the template is not found or an error occurs while updating the template.
    """
    if not templates.check_template_exists(id):
        raise HTTPException(status_code=400, detail="Template not found")
    response = templates.update_template(id, template)
    if response is None:
        raise HTTPException(status_code=500, detail="Error updating template")
    return response


@router.delete("/{id}", status_code=204)
async def delete_template(id: int, request: Request):
    """
    Deletes a template.

    Args:
    - id (int): The ID of the template to be deleted.
    - request (Request): The incoming request.

    Raises:
    - HTTPException: If the template is not found, the user cannot delete the template, or an error occurs while deleting the template.
    """
    if not templates.check_template_exists(id):
        raise HTTPException(status_code=400, detail="Template not found")
    if not templates.user_can_delete_template(id, request.state.current_user.id):
        raise HTTPException(status_code=400, detail="User cannot delete template")
    status = templates.delete_template(id)
    if not status:
        raise HTTPException(status_code=500, detail="Error deleting template")
    return
