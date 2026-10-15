import Image from "next/image";
import Link from "next/link";

/**
 * The one photograph of the site: a real grandstand at a real circuit (Circuit of the Americas, 2012).
 * It sets the mood and is not a picture of any particular weekend, so the caption always names the place.
 * CC BY-SA 3.0, Earl McGehee; the image is only cropped by the layout. Credit and licence are on /about.
 */
export function CircuitPhoto({ className = "", priority = false }: { className?: string; priority?: boolean }) {
  return (
    <figure className={className}>
      <Image
        src="/images/crowd-cota.jpg"
        alt="Fans packing a grandstand beside the track at Circuit of the Americas, with the observation tower behind"
        width={1500}
        height={1000}
        priority={priority}
        // The home server has no image optimiser; the file is already web sized.
        unoptimized
        className="h-56 w-full flex-1 rounded-sm object-cover object-[50%_54%] sm:h-72 lg:h-auto lg:min-h-72"
      />
      <figcaption className="mt-2 flex flex-wrap justify-between gap-x-4 text-xs text-muted">
        <span>Crowds at Circuit of the Americas, 2012</span>
        <Link href="/about#credits" className="underline underline-offset-2 hover:text-accent">
          Photo: Earl McGehee, CC BY-SA 3.0
        </Link>
      </figcaption>
    </figure>
  );
}
