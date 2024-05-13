import glob
import os
import sys

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass


import carla
import random


#objects to manage the connection with the server
client = carla.Client('localhost',2000)
world =  client.get_world()


# Set the simulation to sync mode
init_settings = world.get_settings()
settings = world.get_settings()
settings.synchronous_mode = True


client.load_world('Town05')

vehicle_blueprints = world.get_blueprint_library().filter('*vehicle*')

spawn_points = world.get_map().get_spawn_points()

for i in range(0,10):
    world.try_spawn_actor(random.choice(vehicle_blueprints), random.choice(spawn_points))

port = 8000
tm = client.get_trafficmanager(port)
tm_port = tm.get_port()
vehicles_list = world.get_actors().filter('*vehicle*')
for v in vehicles_list:
    v.set_autopilot(True,tm_port)

danger_car = vehicles_list[0]
tm.set_global_distance_to_leading_vehicle(5)
#tm.global_percentage_speed_difference(10)
for v in vehicles_list: 
  tm.auto_lane_change(v,False)

for actor in vehicles_list:
  tm.update_vehicle_lights(actor, True)


# Set the TM to sync mode
tm.set_synchronous_mode(True)

world.apply_settings(init_settings)
world.tick()


# Spawn pedestrians
SpawnActor = carla.command.SpawnActor
walker_blueprints = world.get_blueprint_library().filter('*walker*')
walk_spawn_points = world.get_map().get_spawn_points()
for i in range(0,10):
    world.try_spawn_actor(random.choice(walker_blueprints), random.choice(walk_spawn_points))

percentagePedestriansCrossing = 30
world.set_pedestrians_cross_factor(percentagePedestriansCrossing)

# Spawn the walker controller
walker_controller_bp = world.get_blueprint_library().find('controller.ai.walker')
walkers_list = world.get_actors().filter('*walker*')
for i in range(len(walkers_list)):
    controller = world.try_spawn_actor(walker_controller_bp, carla.Transform(), walkers_list[i])
    controller.start()
    controller.go_to_location(world.get_random_location_from_navigation())
    #controller.set_max_speed(float((random.choice(walker_blueprints)).get_attribute('speed').recommended_values[i%2]))


# Spawn the ego vehicle the sensors will be attached to
ego_bp = world.get_blueprint_library().find('vehicle.lincoln.mkz_2020')
ego_bp.set_attribute('role_name', 'hero')
ego_vehicle = world.spawn_actor(ego_bp, random.choice(spawn_points))

# Spawn the IMU sensor
imu_blue = world.get_blueprint_library().find('sensor.other.imu')
imu_transform = carla.Transform(carla.Location(x=0.8, z=1.7))
imu_sensor = world.spawn_actor(imu_blue, imu_transform, attach_to=ego_vehicle)

imu_sensor.listen(lambda data: print(data))         # TODO: add MQTT-like data communication


# Spawn the collision deterctor sensor
collision_blue = world.get_blueprint_library().find('sensor.other.collision')
collision_transform = carla.Transform(carla.Location(x=0.8, z=1.7))
collision_sensor = world.spawn_actor(collision_blue, collision_transform, attach_to=ego_vehicle)

# Function called when collisions are detected 
def callback(event):
    for actor_id in event:
        vehicle = world_ref().get_actor(actor_id)
        print('Vehicle collision with: %s' % vehicle.type_id)

collision_sensor.listen(callback)         # TODO: add MQTT-like data communication


try:
    while True:
        world.tick()
except Exception:
    pass

finally:
    print("Received an interruption. Terminating the program...")
    settings = world.get_settings()
    settings.synchronous_mode = False
    world.apply_settings(settings)
    tm.set_synchronous_mode(False)

    print('\ndestroying %d vehicles' % len(vehicles_list))
    client.apply_batch([carla.command.DestroyActor(x) for x in vehicles_list])
    
    print('\ndestroying %d walkers' % len(walkers_list))
    client.apply_batch([carla.command.DestroyActor(x) for x in walkers_list])
    
    