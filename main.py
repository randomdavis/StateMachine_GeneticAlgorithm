import random
import numpy as np
import time
import pygame
import math


# Hold space to slow down the display
# Hold shift to turn off display
# View the console output for high scores and averages
# Edit the labeled parameters in the Board class's constructor to change the simulation

class Board(object):
    def __init__(self):
        # SIMULATION DIMENSIONS
        self.width = 256
        self.height = 256

        total_tiles = self.width * self.height

        # NUMBER OF PLANTS
        self.num_plants = total_tiles // 100

        # NUMBER OF ANIMALS
        self.num_animals = total_tiles // 100

        # TICKS PER ROUND
        self.ticks_per_round = 500

        # TIME PER SLOWED FRAME
        self.time_per_slow_frame = 0.1

        # NUMBER OF POSSIBLE STATES PER ANIMAL
        self.num_states = 8

        # MUTATION CHANCE PER GENE PER ANIMAL
        self.mutation_chance = 0.001

        # DISPLAY SIZE MULTIPLIER
        self.display_multiplier = 4

        # FITNESS PROBABILITY DISTRIBUTION EXPONENT
        self.probability_exponent = 6.0

        self.generation = 0
        self.ticks = 0
        self.rand = random.SystemRandom()
        self.animals = []
        self.plants = []
        self.walls = []
        self.tiles = [[Tile(x, y) for y in range(self.height)] for x in range(self.width)]
        self.high_score = 0
        self.last_high_score = 0
        self.last_average_score = 0.0

        self.top_ever_scorer = None

    def simulate(self):

        top_scorer = None

        display_width = int(self.width * self.display_multiplier)
        display_height = int(self.height * self.display_multiplier)

        pygame.init()

        pygame.display.set_caption('Gen ' + str(self.generation))

        main_surface = pygame.display.set_mode((display_width, display_height))
        self.show_loading_screen(main_surface)

        cells_surface = pygame.Surface((self.width, self.height))

        self.populate_plants()
        self.populate_animals()

        start_time = time.time()

        while True:
            if pygame.key.get_focused():
                self.display(main_surface, cells_surface)

            for _ in range(self.ticks_per_round):
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        try:
                            print(top_scorer.rules)
                        except AttributeError:
                            pass
                        return

                keys = pygame.key.get_pressed()

                self.step()
                if pygame.key.get_focused():
                    if not keys[pygame.K_LSHIFT]:
                        self.display(main_surface, cells_surface)
                    if keys[pygame.K_SPACE]:
                        frame_time = time.time() - start_time
                        time.sleep(self.time_per_slow_frame if frame_time >= self.time_per_slow_frame
                                   else self.time_per_slow_frame - frame_time)
                        start_time = time.time()

            if pygame.key.get_focused():
                self.show_loading_screen(main_surface)
            self.animals.sort(key=lambda b: b.score, reverse=True)
            top_scorer = self.animals[0]
            total_scores = top_scorer.score
            if top_scorer.score > self.high_score:
                self.high_score = top_scorer.score
                self.top_ever_scorer = top_scorer
                top_scorer.remove_self()

            self.last_high_score = top_scorer.score

            self.generation += 1

            self.print_stats()
            pygame.display.set_caption('Gen ' + str(self.generation) + ', Highest ' + str(self.high_score) + ', High ' +
                                       str(self.last_high_score) + ', Avg {0:.2f}'.format(self.last_average_score))

            old_animals = self.animals
            self.animals = []
            self.plants = []
            self.walls = []
            self.tiles = [[Tile(x, y) for y in range(self.height)] for x in range(self.width)]

            self.populate_plants()

            probability_distribution = np.array([a.score + 1 ** self.probability_exponent for a in old_animals],
                                                dtype='float64')
            probs_sum = probability_distribution.sum()
            if probs_sum != 0:
                probability_distribution /= probability_distribution.sum()

                for animal in old_animals:
                    total_scores += animal.score

                    mate = np.random.choice(old_animals, 1, p=probability_distribution)[0]
                    offspring = mate.breed(animal)

                    offspring.randomize_direction()
                    self.add_animal(parent=animal, offspring=offspring)

                # if there are not yet enough animals living

                while len(self.animals) < self.num_animals:
                    animal = self.rand.choice(old_animals)
                    mate = np.random.choice(old_animals, 1, p=probability_distribution)[0]
                    offspring = mate.breed(animal)
                    offspring.randomize_direction()
                    self.add_animal(parent=animal, offspring=offspring)

            else:
                self.populate_animals()

            self.last_average_score = float(total_scores) / self.num_animals

    def fast_render_rgb(self, surface_pixels):
        back_color = (0, 0, 0)
        animal_color = (255, 64, 0)
        plant_color = (32, 210, 0)
        wall_color = (185, 122, 87)

        packed_surface = np.dtype(
            (np.uint32, {'B': (np.uint8, 0), 'G': (np.uint8, 1), 'R': (np.uint8, 2), 'A': (np.uint8, 3)}))
        a = surface_pixels.astype(packed_surface)

        a['A'].fill(0xff)
        a['R'].fill(back_color[0])
        a['G'].fill(back_color[1])
        a['B'].fill(back_color[2])

        for animal in self.animals:
            x = animal.tile.x
            y = animal.tile.y
            a['R'][x][y], a['G'][x][y], a['B'][x][y] = animal_color

        for plant in self.plants:
            x = plant.tile.x
            y = plant.tile.y
            a['R'][x][y], a['G'][x][y], a['B'][x][y] = plant_color

        for wall in self.walls:
            x = wall.tile.x
            y = wall.tile.y
            a['R'][x][y], a['G'][x][y], a['B'][x][y] = wall_color

        #tiles = np.array(self.tiles, dtype='object').flatten()

        #for tile in tiles:
        #    if tile.state == TileState.WALL:
        #        x = tile.x
        #        y = tile.y
        #        a['R'][x][y], a['G'][x][y], a['B'][x][y] = wall_color

        np.copyto(surface_pixels, a)

    def display(self, main_surface, draw_surface):
        self.fast_render_rgb(pygame.surfarray.pixels2d(draw_surface))
        main_surface.blit(pygame.transform.scale(draw_surface, (main_surface.get_width(), main_surface.get_height())),
                          (0, 0))
        pygame.display.flip()

    def show_loading_screen(self, main_surface):
        loading_font = pygame.font.SysFont('Arial', self.height * self.display_multiplier // 5)
        main_surface.fill((0, 0, 0))
        text_surface = loading_font.render('Loading', False, (0xff, 0xff, 0xff))
        main_surface.blit(text_surface, (0, 0))
        pygame.display.flip()

    def print_stats(self):
        out_string = '-' * self.width + '\n' \
                     + 'High Score: ' + str(self.high_score) + '\n' \
                     + 'Last High Score: ' + str(self.last_high_score) + '\n'\
                     + 'Last Average Score: ' + str(self.last_average_score) + '\n'
        print(out_string)

    def step(self):
        self.populate_plants()
        for animal in self.animals:
            animal.step()
        self.ticks += 1

    def populate_plants(self):
        tries = 0
        while len(self.plants) < self.num_plants:
            while True:
                plant_x = self.rand.randint(0, self.width - 1)
                plant_y = self.rand.randint(0, self.height - 1)
                tile_at = self.tiles[plant_x][plant_y]
                if tile_at.state == TileState.EMPTY:
                    tile_at.state = TileState.PLANT
                    new_plant = Plant(self, tile_at)
                    tile_at.obj = new_plant
                    self.plants.append(new_plant)
                    break
                tries += 1
                if tries > 1000:
                    return

    def add_random_animal(self):
        tries = 0
        while True:
            if tries > 100:
                raise RuntimeError("Couldn't place animal after 100 tries")
            animal_x = self.rand.randint(0, self.width - 1)
            animal_y = self.rand.randint(0, self.height - 1)
            tile_at = self.tiles[animal_x][animal_y]
            if tile_at.state == TileState.EMPTY:
                new_animal = Animal(board=self, tile=tile_at,
                                    direction=self.rand.choice([Direction.NORTH, Direction.EAST,
                                                                Direction.SOUTH, Direction.WEST]),
                                    mutation_chance=self.mutation_chance, num_states=self.num_states)
                new_animal.randomize_rules()
                new_animal.randomize_direction()
                self.animals.append(new_animal)
                tile_at.obj = new_animal
                tile_at.state = TileState.ANIMAL
                break
            tries += 1

    def populate_animals(self):
        for a in range(self.num_animals):
            self.add_random_animal()

    def add_animal(self, parent, offspring):
        for spawn_dist in range(1, 1000):
            try_x = parent.tile.x - spawn_dist
            try_y = parent.tile.y - spawn_dist
            try_range = 1 + (2 * spawn_dist)
            for x_offset in range(try_range):
                for y_offset in range(try_range):
                    gotten_tile = self.get_tile_at(try_x + x_offset, try_y + y_offset)
                    if gotten_tile.state == TileState.EMPTY:
                        offspring.move_to_tile(gotten_tile)
                        self.animals.append(offspring)
                        return
        print(
            "Couldn't place a child for parent at " + str(parent.tile.x) + ", " + str(
                parent.tile.y) + "!")

    def get_tile_at(self, x, y):
        return self.tiles[x % self.width][y % self.height]

    @staticmethod
    def can_move(tile):
        if tile.state in [TileState.EMPTY, TileState.PLANT]:
            return True
        return False

    def move_animal(self, animal):
        old_tile = animal.tile
        new_x = animal.tile.x
        new_y = animal.tile.y

        if animal.direction == Direction.NORTH:
            new_y += 1
        elif animal.direction == Direction.EAST:
            new_x += 1
        elif animal.direction == Direction.SOUTH:
            new_y -= 1
        elif animal.direction == Direction.WEST:
            new_x -= 1

        new_tile = self.get_tile_at(new_x, new_y)
        if new_tile is old_tile:
            raise RuntimeError()
        if self.can_move(new_tile):
            animal.move_to_tile(new_tile)
            old_tile.obj = None
            old_tile.state = TileState.EMPTY
            return True
        else:
            return False


class Action(object):
    TURN_LEFT = 0
    TURN_RIGHT = 1
    FORWARD_MOVE = 2
    DROP_WALL = 3


class TileState(object):
    EMPTY = 0
    ANIMAL = 1
    PLANT = 2
    WALL = 3


class Direction(object):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3


class Tile(object):
    def __init__(self, x, y, obj=None, state=TileState.EMPTY):
        self.obj = obj
        self.state = state
        self.x = x
        self.y = y


class TileObject(object):
    def __init__(self, board, tile):
        self.board = board
        self.tile = tile

    def remove_from_tile(self):
        if self.tile is not None:
            self.tile.obj = None
            self.tile.state = TileState.EMPTY
            self.tile = None


class Plant(TileObject):
    def remove_self(self):
        self.remove_from_tile()
        self.board.plants.remove(self)


class Wall(TileObject):
    def remove_self(self):
        self.remove_from_tile()
        self.board.walls.remove(self)


class Animal(TileObject):
    def __init__(self, board, tile, direction=Direction.NORTH, mutation_chance=0.001, num_states=4):
        super(Animal, self).__init__(board, tile)
        self.tile_states = 4
        self.score = 0
        self.num_states = num_states
        self.num_rules = self.num_states * self.tile_states
        self.actions = [Action.TURN_RIGHT, Action.TURN_LEFT, Action.FORWARD_MOVE, Action.DROP_WALL]
        self.rules = np.zeros((self.tile_states, self.num_states, 2), dtype='uint16')
        self.state = 0  # random.randint(0, num_states - 1)
        self.directions = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
        self.direction = direction
        self.mutation_chance = mutation_chance

    def __str__(self):
        return 'Score: ' + str(self.score) + ' x: ' + str(self.tile.x) + ' y: ' + str(self.tile.y)

    def remove_self(self):
        self.remove_from_tile()
        self.board.animals.remove(self)

    def randomize_direction(self):
        self.direction = self.board.rand.choice(self.directions)

    def move_to_tile(self, tile):
        if tile.state == TileState.PLANT:
            self.score += 1
            tile.obj.remove_self()
        elif tile.obj is not None:
            raise RuntimeError('Tried to move to a non-empty tile')

        self.tile = tile
        tile.obj = self
        tile.state = TileState.ANIMAL

    def randomize_rules(self):
        for ts in range(self.tile_states):
            for st in range(self.num_states):
                rand_action = self.board.rand.choice(self.actions)
                rand_state = self.board.rand.randint(0, self.num_states - 1)

                self.rules[ts, st][0] = rand_action
                self.rules[ts, st][1] = rand_state

    def perform_action(self, action):
        if action == Action.TURN_LEFT:
            self.direction -= 1
            self.direction %= 4
        elif action == Action.TURN_RIGHT:
            self.direction += 1
            self.direction %= 4
        elif action == Action.FORWARD_MOVE:
            self.board.move_animal(animal=self)
        elif action == Action.DROP_WALL:
            old_tile = self.tile
            if self.board.move_animal(animal=self):
                if old_tile.state != TileState.EMPTY:
                    raise RuntimeError()
                old_tile.state = TileState.WALL
                new_wall = Wall(self, old_tile)
                old_tile.obj = new_wall
                self.board.walls.append(new_wall)
        else:
            pass

    def get_visible_tile(self):
        my_x = self.tile.x
        my_y = self.tile.y

        if self.direction == Direction.NORTH:
            return self.board.get_tile_at(my_x, my_y + 1)
        elif self.direction == Direction.EAST:
            return self.board.get_tile_at(my_x + 1, my_y)
        elif self.direction == Direction.SOUTH:
            return self.board.get_tile_at(my_x, my_y - 1)
        elif self.direction == Direction.WEST:
            return self.board.get_tile_at(my_x - 1, my_y)
        else:
            raise RuntimeError('Direction not valid')

    def breed(self, other_animal):
        pivot = self.board.rand.random()

        flattened_rules = self.rules.flat
        flattened_other_rules = other_animal.rules.flat

        pivot_point = int(round(pivot * (len(flattened_rules) - 1)))

        if self.board.rand.choice([True, False]):
            flat_offspring_rules = np.concatenate([flattened_other_rules[:pivot_point], flattened_rules[pivot_point:]])
        else:
            flat_offspring_rules = np.concatenate([flattened_rules[:pivot_point], flattened_other_rules[pivot_point:]])

        offspring = Animal(board=self.board, tile=None, num_states=self.num_states,
                           mutation_chance=self.mutation_chance)
        offspring.rules = flat_offspring_rules.reshape(self.rules.shape)

        num_mutations = len(offspring.rules) * len(offspring.rules[0]) * self.mutation_chance

        definite_mutations = int(math.floor(num_mutations))

        chance = num_mutations - definite_mutations

        if self.board.rand.random() < chance:
            definite_mutations += 1

        for _ in range(definite_mutations):
            random_tile = self.board.rand.choice(offspring.rules)
            random_rule = self.board.rand.choice(random_tile)
            random_rule[0] = self.board.rand.choice(self.actions)
            random_rule[1] = self.board.rand.randint(0, self.num_states - 1)

        offspring.state = self.state

        return offspring

    def step(self):
        rule = self.rules[self.get_visible_tile().state, self.state]
        self.perform_action(rule[0])
        self.state = rule[1]


def main():
    b = Board()
    b.simulate()
    pass

if __name__ == '__main__':
    main()
