package com.mrdooz.rest;

import org.json.JSONObject;

import javax.ws.rs.*;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.Response;
import javax.xml.bind.annotation.XmlRootElement;
import java.sql.*;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Path("/")
public class SeriesService {

    @XmlRootElement
    static class EpisodeState {
        public int seriesId;
        public int season;
        public int episode;
    }

    static Connection conn;

    public SeriesService() {

        try {
            // todo: figure out why this is needed for mysql/tomcat to work..
            Class.forName("com.mysql.jdbc.Driver");
            if (conn == null) {
                conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/haveiseenit", "sqluser", "sqluserpw");
            }
        } catch (ClassNotFoundException | SQLException e) {
            e.printStackTrace();
        }
    }

    @GET
    @Path("/series")
    public Response getAllSeries() {

        try {
            ResultSet result = conn.createStatement().executeQuery("select * from series");
            List<Object> series = new ArrayList<>();

            while (result.next()) {
                JSONObject cur = new JSONObject();
                cur.put("id", result.getInt("id"));
                cur.put("name", result.getString("name"));
                cur.put("imdb_id", result.getString("imdb_id"));
                cur.put("num_seasons", result.getInt("num_seasons"));
                series.add(cur);
            }

            JSONObject res = new JSONObject();
            res.put("series", series);

            return Response.status(200).entity(res.toString()).build();

        } catch (SQLException e) {
            e.printStackTrace();
            return Response.status(500).build();
        }
    }

    @GET
    @Path("/series/{series_id}/{season}/episodes")
    public Response getEpisodesForSeries(@PathParam("series_id") int series_id, @PathParam("season")  int season) {

        try {

            // Get the episodes
            ResultSet episodeResultSet = conn.createStatement().executeQuery(
                    String.format("select * from episodes where series_id = %d and season = %d", series_id, season));

            List<Object> episodes = new ArrayList<>();
            while (episodeResultSet.next()) {
                JSONObject cur = new JSONObject();
                cur.put("episode", episodeResultSet.getInt("episode"));
                cur.put("title", episodeResultSet.getString("title"));
                cur.put("airdate", episodeResultSet.getDate("airdate"));
                cur.put("description", episodeResultSet.getString("description"));
                episodes.add(cur);
            }

            // Get the user episodes
            ResultSet userEpisodes = conn.createStatement().executeQuery(
                    String.format("select * from user_episodes where user_id = 1 and series_id = %d and season = %d", series_id, season));

            List<Integer> seen = new ArrayList<>();
            while (userEpisodes.next()) {
                long page = userEpisodes.getLong("page");
                long mask = userEpisodes.getLong("mask");

                for (long i = 0; i < 64; ++i) {
                    if ((mask & 1) != 0) {
                        seen.add((int)(page + i + 1));
                    }
                    mask >>= 1;

                    if (mask == 0)
                        break;
                }
            }

            JSONObject res = new JSONObject();
            res.put("episodes", episodes);
            res.put("series_id", series_id);
            res.put("season", season);
            res.put("seen", seen);
            return Response.status(200).entity(res.toString()).build();

        } catch (SQLException e) {
            return Response.status(500).build();
        }
    }

    // todo: make post
    @POST
    @Path("/series")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response setEpisodeState(EpisodeState state) {

        // note, the state is stored in a 64-bit int, so only 64 episodes are stored per season page
        int page = state.episode / 64;

        try {
            String sql;
            long mask = 1 << (state.episode-1);

            sql = String.format(
                    "INSERT INTO user_episodes (user_id, series_id, season, page, mask) VALUES " +
                            "(%d, %d, %d, %d, %d) " +
                            "ON DUPLICATE KEY UPDATE mask = mask ^ %d",
                    1, state.seriesId, state.season, page, mask, mask);
            int result = conn.createStatement().executeUpdate(sql);
            return Response.status(200).build();
        } catch (SQLException e) {
            e.printStackTrace();
            return Response.status(500).build();
        }
    }
}
