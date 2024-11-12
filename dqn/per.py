from collections import deque
import matplotlib.pyplot as plt
import random
import numpy as np
import gym
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim


class ReplayBuffer:
    def __init__(self, buffer_size, batch_size):
        self.buffer = deque(maxlen=buffer_size)
        self.batch_size = batch_size

    def add(self, state, action, reward, next_state, done, delta):
        data = (state, action, reward, next_state, done, delta)
        self.buffer.append(data)

    def __len__(self):
        return len(self.buffer)
    
    def get_batch(self):
        sum_delta = 0
        for x in self.buffer:
            sum_delta += x[5]
        
        prob = list(x[5] / sum_delta for x in self.buffer)
        data = random.choices(self.buffer, weights=prob, k=self.batch_size)

        state = torch.tensor(np.stack([x[0] for x in data]))
        action = torch.tensor(np.array([x[1] for x in data]))
        reward = torch.tensor(np.array([x[2] for x in data]))
        next_state = torch.tensor(np.stack([x[3] for x in data]))
        done = torch.tensor(np.array([x[4] for x in data]).astype(np.int32))

        return state, action, reward, next_state, done


class QNet(nn.Module):
    def __init__(self, action_size):
        super().__init__()
        self.l1 = nn.Linear(4, 128)
        self.l2 = nn.Linear(128, 128)
        self.l3 = nn.Linear(128, action_size)

    def forward(self, x):
        x = F.relu(self.l1(x))
        x = F.relu(self.l2(x))
        x = self.l3(x)

        return x
    
class DQNAgent:
    def __init__(self):
        self.gamma = 0.98
        self.lr = 0.0005
        self.epsilon = 0.1
        self.buffer_size = 10000
        self.batch_size = 32
        self.action_size = 2

        self.replay_buffer = ReplayBuffer(self.buffer_size, self.batch_size)
        self.qnet = QNet(self.action_size)
        self.qnet_target = QNet(self.action_size)
        self.optimizer = optim.Adam(self.qnet.parameters(), lr=self.lr)

    def get_action(self, state):
        if np.random.rand() < self.epsilon:
            
            return np.random.choice(self.action_size)
        else:
            state = torch.tensor(state[np.newaxis, :])
            qs = self.qnet(state)
            
            return qs.argmax().item()
        
    def update(self, state, action, reward, next_state, done):
        next_q = self.qnet_target(torch.tensor(state)).max()
        q = self.qnet(torch.tensor(state))[action]
        delta = torch.abs(reward + self.gamma * next_q - q)

        self.replay_buffer.add(state, action, reward, next_state, done, delta)

        if len(self.replay_buffer) < self.batch_size:
            return
        
        state, action, reward, next_state, done = self.replay_buffer.get_batch()
        qs = self.qnet(state)
        q = qs[np.arange(len(action)), action]

        next_qs = self.qnet_target(next_state)
        next_q = next_qs.max(1)[0]

        next_q.detach()
        target = reward + (1 - done) * self.gamma * next_q

        loss_fn = nn.MSELoss()
        loss = loss_fn(q, target)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

    def sync_qnet(self):
        self.qnet_target.load_state_dict(self.qnet.state_dict())


if __name__ == '__main__':
    episodes = 300
    sync_interval = 20
    env = gym.make('CartPole-v1', render_mode='rgb_array')
    agent = DQNAgent()
    reward_history = []

    for episode in range(episodes):
        state = env.reset()[0]
        done = False
        total_reward = 0

        while not done:
            action = agent.get_action(state)
            next_state, reward, terminated, truncated, info = env.step(action)
            done = terminated | truncated

            agent.update(state, action, reward, next_state, done)
            state = next_state
            total_reward += reward

        if episode % sync_interval == 0:
            agent.sync_qnet()

        reward_history.append(total_reward)
        if episode % 10 == 0:
            print("episode :{}, total reward: {}".format(episode, total_reward))

    
    plt.xlabel('Episode')
    plt.ylabel('Total Reward')
    plt.plot(range(len(reward_history)), reward_history)
    plt.show()

    
    agent.epsilon = 0
    state = env.reset()[0]
    done = False
    total_reward = 0

    while not done:
        action = agent.get_action(state)
        next_state, reward, terminated, truncated, info = env.step(action)
        done = terminated | truncated
        state = next_state
        total_reward += reward
        env.render()
    print('Total Reward:', total_reward)
    