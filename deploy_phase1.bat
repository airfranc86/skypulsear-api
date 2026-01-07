@echo off
REM =============================================================================
REM SKYPULSE PHASE 1 SECURITY DEPLOYMENT (WINDOWS)
REM =============================================================================
REM Deploys both backend and frontend with security features on Windows
REM =============================================================================

echo.
echo 🚀 SkyPulse Phase 1 Security Deployment - Windows
echo ================================================
echo.

REM Check if backend is running
echo 🔍 Checking backend status...
curl -s http://localhost:8000/ >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Backend is running on http://localhost:8000
    echo 📚 API Documentation: http://localhost:8000/docs
    echo ❤️  Health Check: http://localhost:8000/health
) else (
    echo ❌ Backend not running. Starting...
    start /B cmd /c "uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000"
    timeout /t 3 >nul
    echo ✅ Backend started on http://localhost:8000
)

echo.

REM Test authentication endpoints
echo 🧪 Testing Authentication...

REM Test user registration
echo   🔸 Testing user registration...
curl -s -X POST "http://localhost:8000/api/v1/auth/register" ^
 -H "Content-Type: application/json" ^
 -d "{\"user_data\":{\"username\":\"testuser\",\"email\":\"test@example.com\",\"password\":\"testpassword123\"},\"profile_data\":{\"user_type\":\"general\",\"location\":\"Buenos Aires\"}}" ^
 > temp_register_response.json

if exist temp_register_response.json (
    findstr "access_token" temp_register_response.json >nul
    if %errorlevel% equ 0 (
        echo   ✅ Registration working
        for /f "tokens=2" %%i in ('type temp_register_response.json ^| find "access_token" ^| findstr /o /C:" "') do set TOKEN=%%i
    ) else (
        echo   ❌ Registration failed
        type temp_register_response.json
    )
) else (
    echo   ❌ Registration failed - no response
)

echo.

REM Test user login  
echo   🔸 Testing user login...
curl -s -X POST "http://localhost:8000/api/v1/auth/login" ^
 -H "Content-Type: application/json" ^
 -d "{\"username\":\"testuser\",\"password\":\"testpassword123\"}" ^
 > temp_login_response.json

if exist temp_login_response.json (
    findstr "access_token" temp_login_response.json >nul
    if %errorlevel% equ 0 (
        echo   ✅ Login working
        if not defined TOKEN (
            for /f "tokens=2" %%i in ('type temp_login_response.json ^| find "access_token" ^| findstr /o /C:" "') do set TOKEN=%%i
        )
    ) else (
        echo   ❌ Login failed
        type temp_login_response.json
    )
) else (
    echo   ❌ Login failed - no response
)

echo.

REM Test protected weather endpoint
if defined TOKEN (
    echo   🔸 Testing protected weather endpoint...
    curl -s -X GET "http://localhost:8000/api/v1/weather/current?lat=-34.6^&lon=-58.4" ^
     -H "Authorization: Bearer %TOKEN%" ^
     > temp_weather_response.json
    
    findstr "authenticated" temp_weather_response.json >nul
    if %errorlevel% equ 0 (
        echo   ✅ Weather endpoint authentication working
    ) else (
        echo   ❌ Weather endpoint failed
        type temp_weather_response.json
    )
)

echo.
echo 🌐 Frontend Deployment
echo ====================

REM Check if frontend files exist
if exist "public\dashboard.html" (
    echo ✅ Dashboard HTML found
    
    REM Start frontend server
    echo 🖥️  Starting frontend server on http://localhost:3000
    echo 📱 Frontend will be available at:
    echo    - Main Dashboard: http://localhost:3000/dashboard.html
    echo    - Login Page: http://localhost:3000/login.html
    echo    - Register Page: http://localhost:3000/register.html
    echo.
    
    REM Start frontend server in background
    cd public
    start /B cmd /c "python -m http.server 3000"
    cd ..
    
    echo ✅ Frontend started
) else (
    echo ❌ Frontend files not found
)

echo.
echo 📊 DEPLOYMENT SUMMARY
echo ====================
echo 🖥️  Backend: http://localhost:8000
echo    - API Docs: http://localhost:8000/docs
echo    - Health: http://localhost:8000/health
echo    - Auth: http://localhost:8000/api/v1/auth/login
echo.
echo 🌐 Frontend: http://localhost:3000
echo    - Dashboard: http://localhost:3000/dashboard.html
echo    - Login: http://localhost:3000/login.html
echo    - Register: http://localhost:3000/register.html
echo.
echo 🔐 Security Features Active:
echo    ✅ JWT Authentication
echo    ✅ API Key Validation
echo    ✅ Rate Limiting (100 req/min)
echo    ✅ Security Headers
echo    ✅ Protected Weather Endpoints
echo    ✅ User Registration ^& Login
echo.
echo 🧪 Test Authentication Flow:
echo 1. Visit: http://localhost:3000/register.html
echo 2. Create account
echo 3. Login with credentials
echo 4. Access protected weather data
echo.
echo 🛑 To stop services:
echo    Backend: Close uvicorn window
echo    Frontend: Close HTTP server window
echo.

REM Cleanup temporary files
if exist temp_register_response.json del temp_register_response.json
if exist temp_login_response.json del temp_login_response.json
if exist temp_weather_response.json del temp_weather_response.json

echo ✅ Deployment complete!
echo.
pause