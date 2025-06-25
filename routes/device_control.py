# from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
# from pydantic import BaseModel
# from typing import Any, Dict, Optional
# from auth import get_current_user
# from services.rest_services import rest_device_service
# import asyncio
# import logging
# # v1.0.0
# router = APIRouter(
#     tags=["device-control"],
#     responses={
#         404: {"description": "Not found"},
#         503: {"description": "Device service unavailable"}
#     }
# )
#
# class DeviceCommand(BaseModel):
#     device_id: str
#     command: str
#     params: Optional[Dict[str, Any]] = None
#
# class CommandResponse(BaseModel):
#     message_id: str
#     status: str
#     device_id: str
#     data: Optional[Dict[str, Any]] = None
#
# # Async command results storage (for synchronous response mode)
# command_results = {}
#
# def store_command_result(result):
#     """Store command result in memory for retrieval"""
#     command_results[result["message_id"]] = result
#
# @router.post("/v1/device/command", response_model=CommandResponse)
# async def send_device_command(
#     command: DeviceCommand,
#     background_tasks: BackgroundTasks,
#     wait_for_response: bool = False,
#     timeout: int = 30,
#     user = Depends(get_current_user)
# ):
#     """
#     Send command to a device through REST API
#
#     - wait_for_response: If True, waits for device to respond before returning
#     - timeout: Maximum time to wait for response (in seconds)
#     """
#     # Create async event for waiting
#     if wait_for_response:
#         event = asyncio.Event()
#
#         def on_response(response):
#             # Store response and set event
#             store_command_result(response)
#             event.set()
#
#         # Send command with callback
#         message_id = rest_device_service.send_command(
#             command.device_id,
#             command.command,
#             command.params,
#             callback=on_response,
#             timeout=timeout
#         )
#
#         if not message_id:
#             raise HTTPException(status_code=404, detail="Device not found")
#
#         # Wait for response with timeout
#         try:
#             await asyncio.wait_for(event.wait(), timeout=timeout)
#             # Return the received response
#             if message_id in command_results:
#                 result = command_results.pop(message_id)
#                 return CommandResponse(
#                     message_id=message_id,
#                     status=result.get("status", "error"),
#                     device_id=command.device_id,
#                     data=result.get("data")
#                 )
#             else:
#                 return CommandResponse(
#                     message_id=message_id,
#                     status="timeout",
#                     device_id=command.device_id
#                 )
#         except asyncio.TimeoutError:
#             return CommandResponse(
#                 message_id=message_id,
#                 status="timeout",
#                 device_id=command.device_id
#             )
#     else:
#         # Fire and forget mode
#         message_id = rest_device_service.send_command(
#             command.device_id,
#             command.command,
#             command.params
#         )
#
#         if not message_id:
#             raise HTTPException(status_code=404, detail="Device not found")
#
#         return CommandResponse(
#             message_id=message_id,
#             status="sent",
#             device_id=command.device_id
#         )
#
# @router.get("/v1/device/command/{message_id}", response_model=CommandResponse)
# async def get_command_result(message_id: str, user = Depends(get_current_user)):
#     """Get the result of a previously sent command"""
#     result = rest_device_service.get_command_result(message_id)
#     if result:
#         return CommandResponse(
#             message_id=message_id,
#             status=result.get("status", "error"),
#             device_id=result.get("device_id", "unknown"),
#             data=result.get("data")
#         )
#     else:
#         raise HTTPException(status_code=404, detail="Command result not found")
#
# @router.post("/v1/device/register")
# async def register_device(device_id: str, device_url: str, user = Depends(get_current_user)):
#     """Register a new device or update existing device URL"""
#     rest_device_service.register_device(device_id, device_url)
#     return {"message": f"Device {device_id} registered successfully"}