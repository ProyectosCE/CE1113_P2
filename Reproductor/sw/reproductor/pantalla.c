#include "pantalla.h"
#include "fat.h"
#include "filtros.h"
#include "player.h"
#include "vga.h"
#include "volumen.h"

/*
 * Distribucion (filas):
 *    0  barra de titulo
 *    2  Cancion N de M
 *  4-8  Titulo, artista, album, archivo, formato
 *   10  estado (reproduciendo / pausado / detenido)
 *   12  tiempo MM:SS / MM:SS y barra de avance
 *   14  volumen con barra
 * 16-20 filtros (SW1-SW0), el activo resaltado
 * 22-27 lista de canciones, la actual resaltada
 *   29  ayuda de los botones
 */
#define C_FONDO     VGA_COLOR(VGA_GRIS, VGA_NEGRO)
#define C_ETIQUETA  VGA_COLOR(VGA_GRIS_OSCURO, VGA_NEGRO)
#define C_VALOR     VGA_COLOR(VGA_BLANCO, VGA_NEGRO)
#define C_DESTACADO VGA_COLOR(VGA_AMARILLO, VGA_NEGRO)
#define C_SIN_DATO  VGA_COLOR(VGA_GRIS_OSCURO, VGA_NEGRO)
#define C_TITULO    VGA_COLOR(VGA_BLANCO, VGA_AZUL)
#define C_AYUDA     VGA_COLOR(VGA_NEGRO, VGA_GRIS)
#define C_SELECCION VGA_COLOR(VGA_NEGRO, VGA_CIAN_CLARO)
#define C_BARRA     VGA_COLOR(VGA_CIAN_CLARO, VGA_NEGRO)
#define C_BARRA_VOL VGA_COLOR(VGA_VERDE_CLARO, VGA_NEGRO)

#define COL_VALOR   11          /* columna donde empiezan los valores de los metadatos */
#define LISTA_FILA  23
#define LISTA_N     5           /* canciones visibles en la lista */
#define BARRA_COL   18
#define BARRA_ANCHO 58
#define VOL_COL     11
#define VOL_ANCHO   30

static int activa;
static uint32_t cambios_vistos, segundos_vistos, volumen_visto;
static filtro_t filtro_visto;
static player_estado_t estado_visto;

/* ---------------- Utilidades ---------------- */

/* Escribe n en decimal con al menos 'digitos' cifras. Devuelve el largo. */
static int numero(char *d, uint32_t n, int digitos)
{
    char t[10];
    int k = 0;
    do {
        t[k++] = (char)('0' + n % 10u);
        n /= 10u;
    } while (n && k < 10);
    while (k < digitos)
        t[k++] = '0';
    for (int i = 0; i < k; ++i)
        d[i] = t[k - 1 - i];
    d[k] = '\0';
    return k;
}

static int copiar(char *d, const char *s)
{
    int k = 0;
    while (s[k]) {
        d[k] = s[k];
        ++k;
    }
    d[k] = '\0';
    return k;
}

static int mm_ss(char *d, uint32_t s)
{
    int k = numero(d, s / 60u, 2);
    d[k++] = ':';
    return k + numero(d + k, s % 60u, 2);
}

static void campo(int fila, const char *etiqueta, const char *valor)
{
    vga_texto(2, fila, etiqueta, C_ETIQUETA, COL_VALOR - 2);
    if (valor && valor[0])
        vga_texto(COL_VALOR, fila, valor, C_VALOR, VGA_COLUMNAS - COL_VALOR - 1);
    else
        vga_texto(COL_VALOR, fila, "(sin dato)", C_SIN_DATO, VGA_COLUMNAS - COL_VALOR - 1);
}

static void barra(int col, int fila, int ancho, uint32_t parte, uint32_t total, uint8_t color)
{
    uint32_t llenas = total ? (parte >= total ? (uint32_t)ancho
                                              : (parte * (uint32_t)ancho) / total) : 0u;
    for (int k = 0; k < ancho; ++k)
        vga_celda(col + k, fila, (uint32_t)k < llenas ? VGA_SIM_LLENO : VGA_SIM_VACIO, color);
}

/* ---------------- Secciones ---------------- */

static void dibujar_fijo(void)
{
    vga_limpiar(C_FONDO);

    vga_repetir(0, 0, VGA_COLUMNAS, ' ', C_TITULO);
    vga_celda(1, 0, VGA_SIM_NOTA, C_TITULO);
    vga_texto(3, 0, "Reproductor de audio WAV", C_TITULO, 0);
    vga_texto(VGA_COLUMNAS - 20, 0, "CE-1113  DE1-SoC", C_TITULO, 0);

    vga_repetir(0, 3, VGA_COLUMNAS, VGA_SIM_LINEA, C_ETIQUETA);
    vga_repetir(0, 15, VGA_COLUMNAS, VGA_SIM_LINEA, C_ETIQUETA);
    vga_repetir(0, 21, VGA_COLUMNAS, VGA_SIM_LINEA, C_ETIQUETA);

    vga_texto(2, 14, "Volumen", C_ETIQUETA, 0);
    vga_texto(2, 16, "Filtro (SW1-SW0)", C_ETIQUETA, 0);
    vga_texto(2, 22, "Canciones en la SD", C_ETIQUETA, 0);

    vga_repetir(0, 29, VGA_COLUMNAS, ' ', C_AYUDA);
    vga_texto(1, 29, "KEY0 Play/Pausa   KEY1 Stop   KEY2 Anterior   KEY3 Siguiente   SW1-0 Filtro",
              C_AYUDA, 0);
}

static void dibujar_cancion(void)
{
    char t[48];
    int k = copiar(t, "Canci\xC3\xB3n ");
    k += numero(t + k, player_cancion() + 1u, 2);
    k += copiar(t + k, " de ");
    numero(t + k, player_total(), 2);
    vga_texto(2, 2, t, C_DESTACADO, 30);

    const wav_info_t *w = player_wav();
    if (!player_usa_sd()) {
        campo(4, "T\xC3\xADtulo", player_titulo());
        campo(5, "Artista", "");
        campo(6, "\xC3\x81lbum", "");
        campo(7, "Archivo", "(no hay canciones .wav en la SD)");
        campo(8, "Formato", "44100 Hz, tono generado");
        return;
    }

    campo(4, "T\xC3\xADtulo", player_titulo());
    campo(5, "Artista", w ? w->artista : "");
    campo(6, "\xC3\x81lbum", w ? w->album : "");
    campo(7, "Archivo", fat_nombre_wav((int)player_cancion()));
    if (w) {
        k = numero(t, w->frecuencia, 1);
        k += copiar(t + k, w->canales == 2 ? " Hz, est\xC3\xA9reo, " : " Hz, mono, ");
        k += numero(t + k, w->bits, 1);
        copiar(t + k, " bits");
        campo(8, "Formato", t);
    } else {
        k = copiar(t, "no se pudo abrir: ");
        copiar(t + k, wav_error(player_error()));
        vga_texto(2, 8, "Formato", C_ETIQUETA, COL_VALOR - 2);
        vga_texto(COL_VALOR, 8, t, VGA_COLOR(VGA_ROJO_CLARO, VGA_NEGRO),
                  VGA_COLUMNAS - COL_VALOR - 1);
    }
}

static void dibujar_lista(void)
{
    int total = (int)player_total();
    int actual = (int)player_cancion();
    if (!player_usa_sd()) {
        vga_texto(4, LISTA_FILA, "(no hay canciones .wav en la SD)", C_SIN_DATO, 70);
        for (int i = 1; i < LISTA_N; ++i)
            vga_repetir(0, LISTA_FILA + i, VGA_COLUMNAS, ' ', C_FONDO);
        return;
    }

    /* Ventana de LISTA_N canciones que contiene a la actual */
    int inicio = actual - LISTA_N / 2;
    if (inicio > total - LISTA_N)
        inicio = total - LISTA_N;
    if (inicio < 0)
        inicio = 0;

    for (int i = 0; i < LISTA_N; ++i) {
        int c = inicio + i, fila = LISTA_FILA + i;
        if (c >= total) {
            vga_repetir(0, fila, VGA_COLUMNAS, ' ', C_FONDO);
            continue;
        }
        char n[8];
        numero(n, (uint32_t)c + 1u, 2);
        int sel = (c == actual);
        uint8_t color = sel ? C_SELECCION : C_VALOR;
        vga_celda(2, fila, sel ? VGA_SIM_FLECHA : ' ', sel ? C_DESTACADO : C_FONDO);
        vga_celda(3, fila, ' ', C_FONDO);
        vga_celda(4, fila, ' ', color);
        vga_texto(5, fila, n, color, 3);
        vga_texto(8, fila, fat_nombre_wav(c), color, 66);
        vga_celda(74, fila, ' ', color);
    }
}

static void dibujar_estado(void)
{
    static const char *const nombres[] = { "Detenido", "Reproduciendo", "Pausado" };
    static const uint8_t simbolos[] = { VGA_SIM_STOP, VGA_SIM_PLAY, VGA_SIM_PAUSA };
    static const uint8_t colores[] = {
        VGA_COLOR(VGA_ROJO_CLARO, VGA_NEGRO),
        VGA_COLOR(VGA_VERDE_CLARO, VGA_NEGRO),
        VGA_COLOR(VGA_AMARILLO, VGA_NEGRO),
    };
    player_estado_t e = player_estado();
    vga_celda(2, 10, simbolos[e], colores[e]);
    vga_texto(4, 10, nombres[e], colores[e], 20);
}

static void dibujar_tiempo(void)
{
    char t[16];
    const wav_info_t *w = player_wav();
    uint32_t s = player_segundos();
    uint32_t total = w ? w->duracion_s : 0u;
    int k = mm_ss(t, s);
    k += copiar(t + k, " / ");
    if (w)
        mm_ss(t + k, total);
    else
        copiar(t + k, "--:--");
    vga_texto(2, 12, t, C_VALOR, 15);
    barra(BARRA_COL, 12, BARRA_ANCHO, s, total, C_BARRA);
}

static void dibujar_volumen(uint32_t v)
{
    char t[8];
    barra(VOL_COL, 14, VOL_ANCHO, v, 100u, C_BARRA_VOL);
    int k = numero(t, v, 1);
    copiar(t + k, " %");
    vga_texto(VOL_COL + VOL_ANCHO + 2, 14, t, C_VALOR, 6);
}

static void dibujar_filtros(filtro_t activo)
{
    static const char *const sw[] = { "00", "01", "10", "11" };
    for (int f = 0; f < 4; ++f) {
        int fila = 17 + f, sel = ((filtro_t)f == activo);
        uint8_t color = sel ? C_SELECCION : C_VALOR;
        vga_celda(2, fila, sel ? VGA_SIM_FLECHA : ' ', sel ? C_DESTACADO : C_FONDO);
        vga_celda(4, fila, ' ', color);
        vga_texto(5, fila, sw[f], color, 3);
        vga_texto(8, fila, filtros_nombre((filtro_t)f), color, 30);
    }
}

/* ---------------- Interfaz ---------------- */

int pantalla_iniciar(void)
{
    activa = vga_iniciar() == 0;
    if (!activa)
        return -1;
    dibujar_fijo();
    cambios_vistos = segundos_vistos = volumen_visto = 0xFFFFFFFFu;
    filtro_visto = (filtro_t)-1;
    estado_visto = (player_estado_t)-1;
    return 0;
}

void pantalla_actualizar(void)
{
    if (!activa)
        return;

    if (player_cambios() != cambios_vistos) {   /* cancion o estado */
        cambios_vistos = player_cambios();
        dibujar_cancion();
        dibujar_lista();
        segundos_vistos = 0xFFFFFFFFu;
    }
    if (player_estado() != estado_visto) {
        estado_visto = player_estado();
        dibujar_estado();
    }
    if (player_segundos() != segundos_vistos) {
        segundos_vistos = player_segundos();
        dibujar_tiempo();
    }
    filtro_t f = filtros_actual();
    if (f != filtro_visto) {
        filtro_visto = f;
        dibujar_filtros(f);
    }
    uint32_t v = volumen_porcentaje();
    if (v != volumen_visto) {
        volumen_visto = v;
        dibujar_volumen(v);
    }
}
