from contextlib import closing
from app.utilities.db import get_session
from app.utilities.logger import logger
from app.models.template import Template, TemplateInDB, CreateTemplate, UpdateTemplate
from app.models.user import User, UserRoleEnum as UR
from typing import List, Dict


def check_template_exists(id: int) -> bool:
    """
    Checks if a template exists in the database.

    Args:
    id (int): The ID of the template to check.

    Returns:
    bool: True if the template exists, False otherwise.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            template = session.query(Template).filter(Template.id == id).first()
            session.close()
            return template is not None
    except Exception as e:
        logger.error(f"Error checking template exists: {e}")
    return False


def get_all_templates(user_id: int) -> Dict[str, List[TemplateInDB]] | None:
    """
    Retrieves all templates for a given user.

    Args:
    user_id (int): The ID of the user.

    Returns:
    Dict[str, List[TemplateInDB]] | None: A dictionary containing default and user templates, or None if an error occurs.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            default_templates = session.query(Template).filter(
                Template.user_id == None
            ).filter(
                Template.is_active == True
            ).all()
            user_templates = session.query(Template).filter(
                Template.user_id == user_id
            ).filter(
                Template.is_active == True
            ).all()
            session.close()
            return {
                "default_templates": [
                    TemplateInDB.model_validate(template) for template in default_templates
                ],
                "user_templates": [
                    TemplateInDB.model_validate(template) for template in user_templates
                ]
            }
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
    return None


def create_template(template_data: CreateTemplate) -> TemplateInDB | None:
    """
    Creates a new template in the database.

    Args:
    template_data (CreateTemplate): The data for the new template.

    Returns:
    TemplateInDB | None: The newly created template, or None if an error occurs.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            template = Template(**template_data.model_dump())
            session.add(template)
            session.commit()
            session.refresh(template)
            session.close()
            return TemplateInDB.model_validate(template)
    except Exception as e:
        logger.error(f"Error creating template: {e}")
    return None


def update_template(id: int, template_data: UpdateTemplate) -> TemplateInDB | None:
    """
    Updates an existing template in the database.

    Args:
    id (int): The ID of the template to update.
    template_data (UpdateTemplate): The updated data for the template.

    Returns:
    TemplateInDB | None: The updated template, or None if an error occurs.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            template = session.query(Template).filter(Template.id == id).first()
            if template is None:
                return None
            template.update(**template_data.model_dump(exclude_none=True))
            session.commit()
            session.refresh(template)
            session.close()
            return TemplateInDB.model_validate(template)
    except Exception as e:
        logger.error(f"Error updating template: {e}")
    return None


def user_can_delete_template(id: int, user_id: int) -> bool:
    """
    Checks if a user has the necessary privileges to delete a template.

    Args:
    id (int): The ID of the template to delete.
    user_id (int): The ID of the user attempting to delete the template.

    Returns:
    bool: True if the user can delete the template, False otherwise.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            template = session.query(Template).filter(Template.id == id).first()
            user = session.query(User).filter(User.id == user_id).first()
            session.close()
            if not template.user_id and user.role_id == UR.AGENT.value:
                logger.error(f"User {user_id} does not have enough privileges to delete template {id}")
                return False
            if template.user_id and template.user_id != user_id:
                logger.error(f"User {user_id} does not own the the template {id}")
                return False
            return True
    except Exception as e:
        logger.error(f"Error checking template deletion privileges: {e}")
    return False


def delete_template(id: int) -> bool:
    """
    Deletes a template from the database.

    Args:
    id (int): The ID of the template to delete.

    Returns:
    bool: True if the template is deleted successfully, False otherwise.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            template = session.query(Template).filter(Template.id == id).first()
            if template is None:
                session.close()
                return False
            session.query(Template).filter(Template.id == id).delete()
            session.commit()
            session.close()
            return True
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
    return False
