cmake_minimum_required(VERSION 3.15)
project(McTradingEngineCpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(WIN32)
    add_definitions(-DNOMINMAX -DWIN32_LEAN_AND_MEAN -D_WIN32_WINNT=0x0A00)
endif()

# Dependencies
find_package(cppzmq CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)
find_package(redis++ CONFIG REQUIRED)

# Link to core_lib (sibling directory)
add_subdirectory(../core_lib core_lib_build)

include_directories(include)
include_directories(../core_lib)
include_directories(../core_lib/include)

add_executable(TradingEngineCpp 
    src/main.cpp
    src/EngineCore.cpp
    src/ConfigManager.cpp
    src/HistoryPreloader.cpp
    src/MarketDataParser.cpp
)

target_link_libraries(TradingEngineCpp PRIVATE 
    cppzmq
    nlohmann_json::nlohmann_json
    mc_core
)

if(TARGET redis++::redis++)
    target_link_libraries(TradingEngineCpp PRIVATE redis++::redis++)
elseif(TARGET redis++::redis++_static)
    target_link_libraries(TradingEngineCpp PRIVATE redis++::redis++_static)
endif()
