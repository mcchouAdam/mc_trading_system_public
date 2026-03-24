cmake_minimum_required(VERSION 3.15)
project(HighPerfWsClient CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(WIN32)
    add_definitions(-DNOMINMAX -DWIN32_LEAN_AND_MEAN -D_WIN32_WINNT=0x0A00)
endif()

# Dependencies - Recommended to provide via vcpkg
# vcpkg install boost-beast boost-asio openssl nlohmann-json redis-plus-plus

find_package(Boost REQUIRED COMPONENTS system thread)
find_package(OpenSSL REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)
find_package(redis++ CONFIG REQUIRED)
find_package(cppzmq CONFIG REQUIRED)

include_directories(include)

add_executable(CppWsClient 
    src/main.cpp 
    src/AppConfig.cpp 
    src/RedisService.cpp 
    src/CapitalWsClient.cpp
    src/ZmqService.cpp
    src/WebSocketSession.cpp
)

# Link dependencies
target_link_libraries(CppWsClient PRIVATE
    Boost::system
    Boost::thread
    OpenSSL::SSL
    OpenSSL::Crypto
    nlohmann_json::nlohmann_json
    cppzmq
)

# For redis-plus-plus, vcpkg exposes different target names if built statically vs dynamically
if(TARGET redis++::redis++)
    target_link_libraries(CppWsClient PRIVATE redis++::redis++)
elseif(TARGET redis++::redis++_static)
    target_link_libraries(CppWsClient PRIVATE redis++::redis++_static)
endif()
