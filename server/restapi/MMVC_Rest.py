import os
import sys

from restapi.mods.trustedorigin import TrustedOriginMiddleware
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from typing import Callable, Optional, Sequence, Literal
from mods.log_control import VoiceChangaerLogger
from voice_changer.VoiceChangerManager import VoiceChangerManager

from restapi.MMVC_Rest_Hello import MMVC_Rest_Hello
from restapi.MMVC_Rest_VoiceChanger import MMVC_Rest_VoiceChanger
from restapi.MMVC_Rest_Fileuploader import MMVC_Rest_Fileuploader
from const import MODEL_DIR_STATIC, UPLOAD_DIR, getFrontendPath, TMP_DIR
from voice_changer.utils.VoiceChangerParams import VoiceChangerParams

logger = VoiceChangaerLogger.get_instance().getLogger()


class ValidationErrorLoggingRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                return await original_route_handler(request)
            except RequestValidationError as exc:  # type: ignore
                print("Exception", request.url, str(exc))
                body = await request.body()
                detail = {"errors": exc.errors(), "body": body.decode()}
                raise HTTPException(status_code=422, detail=detail)

        return custom_route_handler


class MMVC_Rest:
    _instance = None

    @classmethod
    def get_instance(
        cls,
        voiceChangerManager: VoiceChangerManager,
        voiceChangerParams: VoiceChangerParams,
        allowedOrigins: Optional[Sequence[str]] = None,
        port: Optional[int] = None,
    ):
        if cls._instance is None:
            logger.info("[Voice Changer] MMVC_Rest initializing...")
            app_fastapi = FastAPI()
            app_fastapi.router.route_class = ValidationErrorLoggingRoute
            app_fastapi.add_middleware(
                TrustedOriginMiddleware,
                allowed_origins=allowedOrigins,
                port=port
            )                                                                                                                   
                                                                                                                                             
            # Mount frontend directories                                                                                                     
            try:                                                                                                                             
                # getFrontendPath() mengembalikan "../client/demo/dist" saat dijalankan sebagai skrip                                        
                frontend_demo_dist_path = getFrontendPath()                                                                                  
                # Dapatkan path dasar dengan naik dua level direktori                                                                        
                # os.path.dirname('../client/demo/dist') -> ../client/demo                                                                   
                # os.path.dirname('../client/demo') -> ../client                                                                             
                frontend_base_path = os.path.dirname(os.path.dirname(frontend_demo_dist_path)) # Hasilnya: ../client                         
                                                                                                                                             
                print(f"Frontend base path determined as: {frontend_base_path}")                                                             
                                                                                                                                             
                # Mount demo                                                                                                                 
                demo_path = os.path.join(frontend_base_path, "demo", "dist")                                                                 
                print(f"Attempting to mount /front from: {os.path.abspath(demo_path)}") # Gunakan abspath untuk kejelasan                    
                if os.path.isdir(demo_path): # Tambahkan pemeriksaan direktori                                                               
                    app_fastapi.mount(                                                                                                       
                        "/front",                                                                                                            
                        StaticFiles(directory=demo_path, html=True),                                                                         
                        name="front",                                                                                                        
                    )                                                                                                                        
                    print(f"Successfully mounted /front from: {demo_path}")                                                                  
                else:                                                                                                                        
                    print(f"WARNING: Directory not found for /front: {demo_path}")                                                           
                                                                                                                                             
                                                                                                                                             
                # Mount trainer                                                                                                              
                trainer_path = os.path.join(frontend_base_path, "trainer", "dist")                                                           
                print(f"Attempting to mount /trainer from: {os.path.abspath(trainer_path)}") # Gunakan abspath                               
                if os.path.isdir(trainer_path): # Tambahkan pemeriksaan direktori                                                            
                    app_fastapi.mount(                                                                                                       
                        "/trainer",                                                                                                          
                        StaticFiles(directory=trainer_path, html=True),                                                                      
                        name="trainer",                                                                                                      
                    )                                                                                                                        
                    print(f"Successfully mounted /trainer from: {trainer_path}")                                                             
                else:                                                                                                                        
                    print(f"WARNING: Directory not found for /trainer: {trainer_path}")                                                      
                                                                                                                                             
                # Mount recorder                                                                                                             
                recorder_path = os.path.join(frontend_base_path, "recorder", "dist")                                                         
                print(f"Attempting to mount /recorder from: {os.path.abspath(recorder_path)}") # Gunakan abspath                             
                if os.path.isdir(recorder_path): # Tambahkan pemeriksaan direktori                                                           
                    app_fastapi.mount(                                                                                                       
                        "/recorder",                                                                                                         
                        StaticFiles(directory=recorder_path, html=True),                                                                     
                        name="recorder",                                                                                                     
                    )                                                                                                                        
                    print(f"Successfully mounted /recorder from: {recorder_path}")                                                           
                else:                                                                                                                        
                    print(f"WARNING: Directory not found for /recorder: {recorder_path}")                                                    
                                                                                                                                             
            except Exception as e:                                                                                                           
                 print(f"Error mounting frontend directories: {e}")                                                                          
                 # Debugging tambahan jika diperlukan                                                                                        
                 try:                                                                                                                        
                     print(f"Value from getFrontendPath() during exception: {getFrontendPath()}")                                            
                 except Exception as e_inner:                                                                                                
                     print(f"Could not call getFrontendPath() during exception handling: {e_inner}")                                         
                                                                                                                                             
                                                                                                                                             
            # Mount temporary and upload directories                                                                                         
            try:                                                                                                                             
                # Pastikan direktori ada sebelum mount                                                                                       
                os.makedirs(TMP_DIR, exist_ok=True)                                                                                          
                print(f"Attempting to mount /tmp from: {os.path.abspath(TMP_DIR)}")                                                          
                app_fastapi.mount("/tmp", StaticFiles(directory=f"{TMP_DIR}"), name="tmp")                                                   
                print(f"Successfully mounted /tmp from: {TMP_DIR}")                                                                          
                                                                                                                                             
                os.makedirs(UPLOAD_DIR, exist_ok=True)                                                                                       
                print(f"Attempting to mount /upload_dir from: {os.path.abspath(UPLOAD_DIR)}")                                                
                app_fastapi.mount("/upload_dir", StaticFiles(directory=f"{UPLOAD_DIR}"), name="upload_dir")                                  
                print(f"Successfully mounted /upload_dir from: {UPLOAD_DIR}")                                                                
            except Exception as e:                                                                                                           
                 print(f"Error mounting tmp or upload_dir: {e}")                                                                             
                                                                                                                                             
                                                                                                                                             
            # Mount model_dir_static                                                                                                         
            try:                                                                                                                             
                print(f"Attempting to mount /model_dir_static from: {os.path.abspath(MODEL_DIR_STATIC)}")                                    
                if os.path.isdir(MODEL_DIR_STATIC):                                                                                          
                    app_fastapi.mount("/model_dir_static", StaticFiles(directory=f"{MODEL_DIR_STATIC}"), name="model_dir_static")            
                    print(f"Successfully mounted /model_dir_static from: {MODEL_DIR_STATIC}")                                                
                else:                                                                                                                        
                    print(f"WARNING: Directory not found for /model_dir_static: {MODEL_DIR_STATIC}")                                         
            except Exception as e:                                                                                                           
                print(f"Locating or mounting model_dir_static failed: {e}")                                                                  
                                                                                                                                             
            # Tentukan path untuk model_dir utama                                                                                            
            model_dir_path = voiceChangerParams.model_dir                                                                                    
            # Periksa apakah berjalan di macOS DAN sebagai aplikasi terbundel PyInstaller                                                    
            if sys.platform.startswith("darwin") and hasattr(sys, '_MEIPASS'):                                                               
                print("Attempting to determine bundled model_dir path on macOS...")                                                          
                try:                                                                                                                         
                    # Logika untuk menemukan path model_dir saat dibundel                                                                    
                    p1 = os.path.dirname(sys._MEIPASS)                                                                                       
                    p2 = os.path.dirname(p1)                                                                                                 
                    p3 = os.path.dirname(p2)                                                                                                 
                    model_dir_path = os.path.join(p3, voiceChangerParams.model_dir)                                                          
                    print(f"Determined bundled model_dir path: {os.path.abspath(model_dir_path)}")                                           
                except Exception as e:                                                                                                       
                    print(f"Error determining bundled model_dir path on macOS: {e}. Falling back to default.")                               
                    # Kembali ke default jika perhitungan path gagal                                                                         
                    model_dir_path = voiceChangerParams.model_dir                                                                            
            # else: (Tidak perlu else eksplisit di sini, model_dir_path sudah default)                                                       
            #    model_dir_path = voiceChangerParams.model_dir # Path standar jika tidak di macOS terbundel                                  
                                                                                                                                             
            # Mount direktori model yang sudah ditentukan path-nya                                                                           
            try:                                                                                                                             
                print(f"Attempting to mount /{voiceChangerParams.model_dir} from: {os.path.abspath(model_dir_path)}")                        
                if os.path.isdir(model_dir_path):                                                                                            
                    app_fastapi.mount(                                                                                                       
                        f"/{voiceChangerParams.model_dir}", # Pertahankan URL path agar konsisten                                            
                        StaticFiles(directory=model_dir_path),                                                                               
                        name="model_dir_main",                                                                                               
                    )                                                                                                                        
                    print(f"Successfully mounted /{voiceChangerParams.model_dir} from: {model_dir_path}")                                    
                else:                                                                                                                        
                    print(f"WARNING: Directory not found for model_dir_main: {model_dir_path}")                                              
            except Exception as e:                                                                                                           
                 print(f"Error mounting model directory '{model_dir_path}': {e}")                                                            
                                                                                                                                             
                                                                                                                                             
            # Include API routers                                                                                                            
            restHello = MMVC_Rest_Hello()
            app_fastapi.include_router(restHello.router)
            restVoiceChanger = MMVC_Rest_VoiceChanger(voiceChangerManager)
            app_fastapi.include_router(restVoiceChanger.router)
            fileUploader = MMVC_Rest_Fileuploader(voiceChangerManager)
            app_fastapi.include_router(fileUploader.router)

            cls._instance = app_fastapi
            logger.info("[Voice Changer] MMVC_Rest initializing... done.")
            return cls._instance

        return cls._instance
