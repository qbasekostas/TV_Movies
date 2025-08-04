import org.apache.commons.text.StringEscapeUtils;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedWriter;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class ErtflixScraper {

    // --- API Endpoints ---
    private static final String LIST_API_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent";
    private static final String TILE_DETAIL_API_URL = "https://api.app.ertflix.gr/v1/tile/GetTile";
    private static final String PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent";

    // --- Σταθερές ---
    private static final String DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3";
    private static final String OUTPUT_FILE = "ertflix_playlist.m3u8";
    private static final String USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36";
    private static final String REFERER = "https://www.ertflix.gr/";

    // Οι κατηγορίες που θα σαρωθούν
    private static final Map<String, String> CATEGORIES = new HashMap<>() {{
        put("Όλες οι Ταινίες", "oles-oi-tainies-1");
        put("Κωμωδίες", "komodies-1");
        put("Ρομαντικές", "romantikes");
        put("Περιπέτειες", "peripeteies-1");
        put("Δραματικές", "dramatikes");
        put("Θρίλερ", "copy-of-thriler");
        put("Βιογραφίες", "biographies-1");
        put("Σινεφίλ", "sinephil");
        put("Ελληνικός Κινηματογράφος", "ellenikos-kinematographos");
        put("Μικρές Ιστορίες", "mikres-istories");
        put("Παιδικές Ταινίες", "paidikes-tainies-1");
    }};

    public static void main(String[] args) throws IOException, InterruptedException {
        // Δημιουργούμε ένα HttpClient που θα επαναχρησιμοποιείται
        HttpClient client = HttpClient.newBuilder().version(HttpClient.Version.HTTP_2).build();
        
        Map<String, MovieData> finalPlaylist = new HashMap<>();
        System.out.println("--- Έναρξη σάρωσης όλων των κατηγοριών από το API ---");

        for (Map.Entry<String, String> category : CATEGORIES.entrySet()) {
            String categoryName = category.getKey();
            String sectionCodename = category.getValue();
            System.out.printf("\n>>> Επεξεργασία κατηγορίας: %s%n", categoryName);

            try {
                // Βήμα 1: Λήψη της λίστας των ταινιών για την κατηγορία
                String listUrl = String.format("%s?platformCodename=www§ionCodename=%s", LIST_API_URL, sectionCodename);
                JSONObject listData = fetchJson(client, listUrl);
                
                JSONArray moviesInCategory = listData.getJSONObject("SectionContent").getJSONArray("TilesIds");
                if (moviesInCategory.isEmpty()) {
                    System.out.println("  -> Δεν βρέθηκαν ταινίες σε αυτή την κατηγορία.");
                    continue;
                }
                
                System.out.printf("  -> Βρέθηκαν %d ταινίες. Έναρξη επεξεργασίας...%n", moviesInCategory.length());

                // Βήμα 2: Επεξεργασία κάθε ταινίας
                for (int i = 0; i < moviesInCategory.length(); i++) {
                    JSONObject tile = moviesInCategory.getJSONObject(i);
                    String codename = tile.optString("Codename", null);
                    
                    if (codename == null || finalPlaylist.containsKey(codename)) {
                        continue; // Παράλειψη αν δεν έχει codename ή αν υπάρχει ήδη
                    }

                    try {
                        // 2a: Λήψη Τίτλου και Εικόνας
                        String detailUrl = String.format("%s?platformCodename=www&codename=%s", TILE_DETAIL_API_URL, codename);
                        JSONObject detailData = fetchJson(client, detailUrl);
                        String title = StringEscapeUtils.unescapeHtml4(detailData.optString("Title", codename).strip());
                        String posterUrl = detailData.optString("Poster", "");
                        System.out.printf("    Επεξεργασία %d/%d: %s%n", i + 1, moviesInCategory.length(), title);

                        // 2b: Λήψη Stream URL
                        long timestamp = System.currentTimeMillis();
                        String playerUrl = String.format("%s?platformCodename=www&deviceKey=%s&codename=%s&t=%d", PLAYER_API_URL, DEVICE_KEY, codename, timestamp);
                        JSONObject playerData = fetchJson(client, playerUrl);

                        String finalUrl = findBestStreamUrl(playerData);

                        if (finalUrl != null) {
                            finalPlaylist.put(codename, new MovieData(title, finalUrl, posterUrl, categoryName));
                        }
                    } catch (Exception e) {
                         // Αγνοούμε τα σφάλματα για μεμονωμένες ταινίες για να συνεχίσει το script
                    }
                    Thread.sleep(50); // Μικρή παύση
                }
            } catch (Exception e) {
                 // Αγνοούμε σφάλματα ολόκληρης κατηγορίας
            }
        }

        // Βήμα 3: Εγγραφή του αρχείου
        writeM3UFile(finalPlaylist);
    }

    // Βοηθητική μέθοδος για την εκτέλεση HTTP GET requests
    private static JSONObject fetchJson(HttpClient client, String url) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("User-Agent", USER_AGENT)
                .header("Referer", REFERER)
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        return new JSONObject(response.body());
    }

    // Βοηθητική μέθοδος για την εύρεση του καλύτερου stream URL
    private static String findBestStreamUrl(JSONObject playerData) {
        String goodM3u8 = null, mpdUrl = null;
        if (playerData.has("MediaFiles")) {
            JSONArray mediaFiles = playerData.getJSONArray("MediaFiles");
            for (int i = 0; i < mediaFiles.length(); i++) {
                JSONObject mediaFile = mediaFiles.getJSONObject(i);
                if (mediaFile.has("Formats")) {
                    JSONArray formats = mediaFile.getJSONArray("Formats");
                    for (int j = 0; j < formats.length(); j++) {
                        JSONObject format = formats.getJSONObject(j);
                        String url = format.optString("Url", "");
                        if (url.endsWith(".m3u8") && !url.contains("/output1/")) {
                            goodM3u8 = url;
                            break;
                        } else if (url.endsWith(".mpd")) {
                            mpdUrl = url;
                        }
                    }
                }
                if (goodM3u8 != null) break;
            }
        }
        String finalUrl = (goodM3u8 != null) ? goodM3u8 : mpdUrl;
        if (finalUrl != null && finalUrl.endsWith(".mpd")) {
            return finalUrl.replace("/index.mpd", "/playlist.m3u8");
        }
        return finalUrl;
    }
    
    // Βοηθητική μέθοδος για την εγγραφή του τελικού αρχείου
    private static void writeM3UFile(Map<String, MovieData> playlist) throws IOException {
        if (playlist.isEmpty()) {
            System.out.println("\nΔεν βρέθηκαν ταινίες με έγκυρο stream.");
            return;
        }
        try (BufferedWriter writer = Files.newBufferedWriter(Paths.get(OUTPUT_FILE))) {
            writer.write("#EXTM3U\n");
            for (MovieData movie : playlist.values()) {
                String logoTag = movie.posterUrl.isEmpty() ? "" : String.format("tvg-logo=\"%s\"", movie.posterUrl);
                String infoLine = String.format("#EXTINF:-1 group-title=\"%s\" %s,%s\n", movie.groupTitle, logoTag, movie.title);
                String userAgentLine = String.format("#EXTVLCOPT:user-agent=%s\n", USER_AGENT);
                
                writer.write(infoLine);
                writer.write(userAgentLine);
                writer.write(movie.streamUrl + "\n");
            }
        }
        System.out.printf("\nΤο αρχείο %s δημιουργήθηκε με %d μοναδικές ταινίες!%n", OUTPUT_FILE, playlist.size());
    }

    // Βοηθητική κλάση για την αποθήκευση των δεδομένων της ταινίας
    private static class MovieData {
        final String title;
        final String streamUrl;
        final String posterUrl;
        final String groupTitle;
        MovieData(String title, String streamUrl, String posterUrl, String groupTitle) {
            this.title = title;
            this.streamUrl = streamUrl;
            this.posterUrl = posterUrl;
            this.groupTitle = groupTitle;
        }
    }
}
