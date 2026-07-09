cmake_minimum_required(VERSION 3.18)
project(hex_alphazero LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -funroll-loops")

# ------------------------------------------------------------------ #
# Dependencies
# ------------------------------------------------------------------ #
find_package(Torch REQUIRED)          # LibTorch (neural network)
find_package(Threads REQUIRED)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${TORCH_CXX_FLAGS}")

include(FetchContent)

# yaml-cpp for configuration files
FetchContent_Declare(
    yaml-cpp
    GIT_REPOSITORY https://github.com/jbeder/yaml-cpp.git
    GIT_TAG 0.8.0
)
set(YAML_CPP_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(YAML_CPP_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(yaml-cpp)

# stb (header-only PNG load/save for asset-based visualization)
FetchContent_Declare(
    stb
    GIT_REPOSITORY https://github.com/nothings/stb.git
    GIT_TAG 5c205738c191bcb0abc65c4febfa9bd25ff35234
)
FetchContent_GetProperties(stb)
if(NOT stb_POPULATED)
    FetchContent_Populate(stb)
endif()

# ------------------------------------------------------------------ #
# Core game engine library
# ------------------------------------------------------------------ #
add_library(hex_engine STATIC
    src/hex_geometry.cpp
    src/game_state.cpp
    src/game_rules.cpp
    src/action_space.cpp
    src/config.cpp
)
target_include_directories(hex_engine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(hex_engine PUBLIC yaml-cpp Threads::Threads)

# ------------------------------------------------------------------ #
# RL library (network, MCTS, self-play, training)
# ------------------------------------------------------------------ #
add_library(hex_rl STATIC
    src/neural_net.cpp
    src/mcts.cpp
    src/replay_buffer.cpp
    src/self_play.cpp
    src/trainer.cpp
)
target_include_directories(hex_rl PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(hex_rl PUBLIC hex_engine "${TORCH_LIBRARIES}")
set_property(TARGET hex_rl PROPERTY CXX_STANDARD 17)

# ------------------------------------------------------------------ #
# Visualization library
# ------------------------------------------------------------------ #
add_library(hex_viz STATIC
    src/visualizer.cpp
)
target_include_directories(hex_viz PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_include_directories(hex_viz PRIVATE ${stb_SOURCE_DIR})
target_link_libraries(hex_viz PUBLIC hex_engine)

# ------------------------------------------------------------------ #
# Executables
# ------------------------------------------------------------------ #
add_executable(train src/train_main.cpp)
target_link_libraries(train PRIVATE hex_rl hex_viz)

add_executable(visualize src/visualize_main.cpp)
target_link_libraries(visualize PRIVATE hex_rl hex_viz)

# copy configs next to binaries for convenience
add_custom_command(TARGET train POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        ${CMAKE_CURRENT_SOURCE_DIR}/configs
        ${CMAKE_CURRENT_BINARY_DIR}/configs
)