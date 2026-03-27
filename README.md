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
    jwt: string,
    expires_in: number
} | {
    error: string
}
```

### Get leaderboard

#### $\color{Green}{\textsf{GET}}$ `/leaderboards`

###### Search Parameters

| Name   | Data type       | Description                                                  | Default Value          |
| ------ | --------------- | ------------------------------------------------------------ | ---------------------- |
| offset | number          | Determine the offset of the returned list of users           | 0                      |
| limit  | number          | Determine the amount of users returned. <br> Min: 1, Max: 50 | 10                     |
| order  | "asc" \| "desc" | Determine the order by games won direction                   | "desc" (highest first) |

###### Response Schema

```ts
{
    username: string,
    games_won: number,
    games_played: number
}[]
```

## Authorized Routes

> [!Tip]
> You can use `anon` for `<str:username>` path variable if you want to avoid passing jwt token on the auth headers

### Start a game

#### $\color{Orange}{\textsf{POST}}$ `/<str:username>/play`

###### Request Headers

`Authorization` - contains the `jwt` token to be used for authentication

###### No Request Body Needed

###### Response Body

```ts
{
  game_code: string;
}
```

### View current state of a game

#### $\color{Green}{\textsf{GET}}$ `/<str:username>/<str:game_code>`

###### Request Headers

`Authorization` - contains the `jwt` token to be used for authentication

###### Response Body

```ts
{
    tries_left: number,
    tries: string[] //*
    word_length: number,
    created_at: string // ISO8601
} | { error: string }
```

\*`tries` - a list of strings where each characters could be followed by:

- `/` - the character before is within the word and is in the correct position
- `+` - The character before is within the word but is not in the correct position

### Guess a word

#### $\color{Orange}{\textsf{POST}}$ `/<str:username>/<str:game_code>/<str:input>`

###### Request Headers

`Authorization` - contains the `jwt` token to be used for authentication

###### Response Body

```ts
{
    tries_left: number,
    tries: string[] //*
    word_length: number,
    created_at: string // ISO8601
} | { error: string }
```

### Get account state

#### $\color{Green}{\textsf{GET}}$ `/<str:username>`

###### Request Headers

`Authorization` - contains the `jwt` token to be used for authentication

###### Search Parameters

| Name   | Data type       | Description                                                  | Default Value          |
| ------ | --------------- | ------------------------------------------------------------ | ---------------------- |
| offset | number          | Determine the offset of the returned list of games           | 0                      |
| limit  | number          | Determine the amount of games returned. <br> Min: 1, Max: 10 | 10                     |
| order  | "asc" \| "desc" | Determine the order by games by date creation                | "desc" (highest first) |

###### Response Body

```ts
{
    games_played: number,
    games_won: number,
    games: {
        code: string,
        won: boolean,
        tries_left:  number,
        created_at: string // ISO8601
    }[]
}
```
