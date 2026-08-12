"""Device registration, preferences and the saved-jobs list."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..interests import PROFILES_BY_SLUG
from ..models import Device, Job, SavedJob, SaveState, utcnow
from ..schemas import DeviceOut, DevicePatchIn, DeviceRegisterIn, SavedJobOut, SaveIn
from ..serializers import job_summary
from .deps import DeviceDep, SessionDep

router = APIRouter(prefix="/v1/devices", tags=["devices"])


def _clean_interests(slugs: list[str]) -> list[str]:
    return [s for s in slugs if s in PROFILES_BY_SLUG]


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def register_device(session: SessionDep, body: DeviceRegisterIn) -> DeviceOut:
    """Idempotent: re-registering the same APNs token updates it in place."""
    device = session.scalar(select(Device).where(Device.apns_token == body.apns_token))
    if device is None:
        device = Device(apns_token=body.apns_token)
        session.add(device)

    device.install_id = body.install_id or device.install_id
    device.display_name = body.display_name or device.display_name
    device.interests = _clean_interests(body.interests) or device.interests or []
    device.push_enabled = body.push_enabled
    device.internships_only = body.internships_only
    device.min_score = body.min_score
    device.timezone = body.timezone
    device.quiet_hours_enabled = body.quiet_hours_enabled
    device.app_version = body.app_version
    device.environment = body.environment
    device.is_active = True
    device.last_seen_at = utcnow()

    session.commit()
    session.refresh(device)
    return DeviceOut.model_validate(device)


@router.get("/{token}", response_model=DeviceOut)
def read_device(device: DeviceDep) -> DeviceOut:
    return DeviceOut.model_validate(device)


@router.patch("/{token}", response_model=DeviceOut)
def update_device(session: SessionDep, device: DeviceDep, body: DevicePatchIn) -> DeviceOut:
    data = body.model_dump(exclude_unset=True)
    if "interests" in data and data["interests"] is not None:
        data["interests"] = _clean_interests(data["interests"])
    for key, value in data.items():
        if value is not None:
            setattr(device, key, value)
    device.last_seen_at = utcnow()
    session.commit()
    session.refresh(device)
    return DeviceOut.model_validate(device)


@router.delete("/{token}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_device(session: SessionDep, device: DeviceDep) -> None:
    device.is_active = False
    device.push_enabled = False
    session.commit()


# --- saved jobs ------------------------------------------------------------


@router.get("/{token}/saved", response_model=list[SavedJobOut])
def list_saved(session: SessionDep, device: DeviceDep) -> list[SavedJobOut]:
    rows = session.execute(
        select(SavedJob, Job)
        .join(Job, Job.id == SavedJob.job_id)
        .where(SavedJob.device_id == device.id, SavedJob.state != SaveState.dismissed)
        .order_by(SavedJob.created_at.desc())
        .options(selectinload(Job.company), selectinload(Job.matches))
    ).all()

    return [
        SavedJobOut(
            job=job_summary(job),
            state=saved.state.value,
            note=saved.note,
            created_at=saved.created_at,
        )
        for saved, job in rows
    ]


@router.post("/{token}/saved", response_model=SavedJobOut, status_code=status.HTTP_201_CREATED)
def save_job(session: SessionDep, device: DeviceDep, body: SaveIn) -> SavedJobOut:
    job = session.get(Job, body.job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")

    saved = session.scalar(
        select(SavedJob).where(SavedJob.device_id == device.id, SavedJob.job_id == job.id)
    )
    if saved is None:
        saved = SavedJob(device_id=device.id, job_id=job.id)
        session.add(saved)

    saved.state = SaveState(body.state)
    saved.note = body.note
    session.commit()
    session.refresh(saved)

    return SavedJobOut(
        job=job_summary(job), state=saved.state.value, note=saved.note, created_at=saved.created_at
    )


@router.delete("/{token}/saved/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsave_job(session: SessionDep, device: DeviceDep, job_id: int) -> None:
    saved = session.scalar(
        select(SavedJob).where(SavedJob.device_id == device.id, SavedJob.job_id == job_id)
    )
    if saved is not None:
        session.delete(saved)
        session.commit()
