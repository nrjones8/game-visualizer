library(ggplot2)


data <- read.csv('data/with_clusters.csv')

cleanup <- function(df) {
  df$round_num <- as.factor(df$round_num)
  df$rank_diff <- as.factor(df$rank_diff)
  #df$cluster_num <- as.factor(df$cluster_num)
  
  return(df)
}

plot_timeline <- function(df) {
  # Opacity based on rank diff?
  # Opacity based on upset?
  min_diff <- min(df$diff_score)
  max_diff <- max(df$diff_score)
  max_time <- max(df$time)
  
  round_two <- which(df$round == 2)
  round_three <- which(df$round == 3)
  
  # HEATMAP??
  #g <- ggplot(df[which(df$game_id == 'CCAR-UVA'), ], aes(x = time, y = diff_score)) +
  g <- ggplot(df[, ], aes(x = time, y = diff_score)) +
    geom_line(aes(color = rank_diff, group = game_id)) +
    geom_hline(yintercept=0) +
    scale_x_continuous(limits = c(0, max_time)) +
    scale_y_continuous(limits = c(min_diff, max_diff)) +
    #scale_colour_brewer(type="seq", palette="Blues")
    scale_colour_brewer(type="seq", palette="RdBu")
  
  print(g)
}

heatmap <- function(df) {
  
  # Don't need to sort if using facet_grid
  max_score <- 15
  df$rounded_diff_score <- sapply(df$diff_score, function(score) {
    ifelse(score > 0, min(score, max_score), max(score, -max_score))
  })
  
  
  # Thanks to tutorial here: http://learnr.wordpress.com/2010/01/26/ggplot2-quick-heatmap-plotting/
  # Also good: http://quantcorner.wordpress.com/2013/11/02/creating-a-heatmap-to-visualize-returns-with-r-ggplot2/
  
  # TODO limits on heatmap -- lead of over 10 --> solid color?
  heat <- ggplot(df, aes(time, game_id)) +
    geom_tile(aes(fill = rounded_diff_score), color = 'white') +
    scale_fill_gradient2(low = 'red', high = 'blue') +
    facet_grid(rank_diff ~ ., scales = 'free', space = 'free')
  
  print(heat)
}