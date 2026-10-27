from src.engine.dynamic_profile import DynamicProfile
from src.engine.nodes import DynamicNode
from src.config import engine_default, vehicle_default


def make_profile(sample_segment, velocities=(0, 6, 11, 16, 20)):
    nodes = []
    distances = [0, 3, 8, 15, 25]
    for velocity, distance in zip(velocities, distances):
        node = DynamicNode(sample_segment, vehicle_default, engine_default)
        node.initialize(velocity=velocity)
        node.dist = distance
        node.time = distance / velocity if velocity else 0
        node.dt = 1.0
        node.acc = 1.0
        nodes.append(node)
    return DynamicProfile(engine_default, nodes)


def test_indexing_points_to_next_node(sample_segment):
    profile = make_profile(sample_segment)
    profile.indexing(velocity_interval=5, distance_interval=5)

    assert profile.velocity_index == [0, 1, 2, 3, 4]
    assert profile.distance_index == [0, 2, 3, 3, 4, 4]


def test_node_at_velocity_interpolates_between_nodes(sample_segment):
    profile = make_profile(sample_segment)
    profile.indexing(velocity_interval=5, distance_interval=5)

    node = profile.node_at(velocity=8, precise=True)

    assert node.velocity == 8
    assert profile.nodes[1].dist < node.dist < profile.nodes[2].dist


def test_node_at_distance_interpolates_between_nodes(sample_segment):
    profile = make_profile(sample_segment)
    profile.indexing(velocity_interval=5, distance_interval=5)

    node = profile.node_at(distance=6, precise=True)

    assert node.dist == 6
    assert profile.nodes[1].dist < node.dist < profile.nodes[2].dist


def test_binary_search_interpolates_velocity_and_distance(sample_segment):
    profile = make_profile(sample_segment)
    profile.indexing(velocity_interval=5, distance_interval=5)

    for velocity in (0, 3, 6, 8, 11, 15, 16, 19, 20):
        node = profile.node_at(velocity=velocity, precise=True)
        assert node.velocity == velocity

    for distance in (0, 1, 3, 6, 8, 12, 15, 20, 25):
        node = profile.node_at(distance=distance, precise=True)
        assert node.dist == distance


def test_binary_search_handles_deceleration(sample_segment):
    profile = make_profile(sample_segment, velocities=(20, 16, 11, 6, 0))
    profile.indexing(velocity_interval=5, distance_interval=5)

    for velocity in (20, 19, 16, 14, 11, 8, 6, 3, 0):
        node = profile.node_at(velocity=velocity, precise=True)
        assert node.velocity == velocity


def test_default_lookup_interpolates_from_bucket(sample_segment):
    profile = make_profile(sample_segment)
    profile.indexing(velocity_interval=5, distance_interval=5)

    assert profile.node_at(velocity=8).velocity == 8
    assert profile.node_at(distance=6).dist == 6
