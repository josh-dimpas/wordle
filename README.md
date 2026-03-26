# Wordle API

A wordle game

### Table of Contents

- [Create account](#create-account)
- [Login](#login)
- [Start a game](#start-a-game)
- [View current state of a game](#view-current-state-of-a-game)
- [Guess a word](#guess-a-word)
- [Get accounts state](#get-accounts-state)
- [Get leaderboard](#get-leaderboard)

## Endpoints

### Create account

#### $\color{Orange}{\textsf{POST}}$ `/register`

###### Request Body

```ts
{
    username: string,
    password: string
}
```

###### Response Schema

```ts
{
    message: "Success"
} | {
    error: string
}
```

### Login

#### $\color{Orange}{\textsf{POST}}$ `/login`

### Get leaderboard

#### $\color{Green}{\textsf{GET}}$ `/leaderboard`

### Start a game

### View current state of a game

### Guess a word

### Get accounts state
